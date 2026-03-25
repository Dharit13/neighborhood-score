"""
Background pipeline: compute walkability scores using our DB + Google Maps Places API.
No Overpass dependency.

Data sources:
  1. PostGIS queries on our own tables (hospitals, schools, bus_stops, metro_stations, police_stations)
  2. Google Maps Places API Nearby Search (groceries, restaurants, pharmacies, parks)

NEWS-India subscales mapped to available data:
  1. Land-use diversity: count of distinct facility types within 1km
  2. Land-use access: avg distance to nearest of each facility type
  3. Transit connectivity: transit points within 1km (proxy for street grid quality)
  4. Walking infrastructure: police + transit density (proxy for pedestrian activity)
  5. Green space: park count within 1km (Google Maps)
  6. Commercial access: grocery + restaurant + pharmacy count (Google Maps)

Usage: python -m app.pipelines.pipeline_walkability [--name NEIGHBORHOOD]
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

import httpx
from app.db import get_sync_conn

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
NUM_SUBSCALES = 6
RADIUS_M = 1000


def _count_db_facilities(cur, lat: float, lon: float) -> dict:
    """Count facilities from our own tables within 1km using PostGIS."""
    counts = {}
    tables = [
        ("hospitals", "hospitals"),
        ("schools", "schools"),
        ("bus_stops", "bus_stops"),
        ("metro_stations", "metro_stations"),
        ("police_stations", "police_stations"),
        ("train_stations", "train_stations"),
        ("tech_parks", "tech_parks"),
    ]
    for label, table in tables:
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE ST_DWithin(geog, ST_Point(%s, %s)::geography, %s)",
            (lon, lat, RADIUS_M),
        )
        counts[label] = cur.fetchone()[0]

    # Nearest distance for each type
    distances = {}
    for label, table in tables:
        cur.execute(
            f"""SELECT ST_Distance(geog, ST_Point(%s, %s)::geography) / 1000.0
                FROM {table}
                ORDER BY geog <-> ST_Point(%s, %s)::geography
                LIMIT 1""",
            (lon, lat, lon, lat),
        )
        row = cur.fetchone()
        distances[label] = row[0] if row else 10.0

    return {"counts": counts, "distances": distances}


def _fetch_google_places(lat: float, lon: float, place_type: str) -> int:
    """Count places of a type within 1km using Google Maps Nearby Search."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lon}",
                    "radius": RADIUS_M,
                    "type": place_type,
                    "key": GOOGLE_MAPS_API_KEY,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return len(data.get("results", []))
    except Exception as e:
        print(f"    Google Places error for {place_type}: {e}")
    return 0


def _compute_score(db_data: dict, amenities: dict) -> float:
    """Compute NEWS-India walkability score from DB + Google Maps data."""
    counts = db_data["counts"]
    distances = db_data["distances"]

    # Subscale 1: Land-use diversity (0-100)
    # How many distinct facility types exist within 1km
    types_present = sum(1 for v in counts.values() if v > 0)
    google_types = sum(1 for v in amenities.values() if v > 0)
    total_types = types_present + google_types
    max_types = len(counts) + len(amenities)  # 7 DB + 4 Google = 11
    diversity = min(total_types / max_types, 1.0) * 100

    # Subscale 2: Land-use access (0-100)
    # Average proximity to nearest of each DB facility type
    # decay: within 0.3km = full, beyond 1km = zero
    access_scores = []
    for dist in distances.values():
        if dist <= 0.3:
            access_scores.append(1.0)
        elif dist <= 1.0:
            access_scores.append(1.0 - (dist - 0.3) / 0.7)
        else:
            access_scores.append(0.0)
    access = (sum(access_scores) / max(len(access_scores), 1)) * 100

    # Subscale 3: Transit connectivity (0-100)
    # Bus stops + metro within 1km as proxy for connected street grid
    transit_count = counts.get("bus_stops", 0) + counts.get("metro_stations", 0) + counts.get("train_stations", 0)
    connectivity = min(transit_count / 5.0, 1.0) * 100

    # Subscale 4: Walking infrastructure (0-100)
    # Police + transit density as proxy for pedestrian-active streets
    infra_points = counts.get("police_stations", 0) + transit_count
    infra = min(infra_points / 8.0, 1.0) * 100

    # Subscale 5: Green space (0-100)
    parks = amenities.get("park", 0)
    green = min(parks / 3.0, 1.0) * 100

    # Subscale 6: Commercial access (0-100)
    commercial = amenities.get("grocery_or_supermarket", 0) + amenities.get("restaurant", 0) + amenities.get("pharmacy", 0)
    commercial_score = min(commercial / 15.0, 1.0) * 100

    # Equal weight per NEWS-India
    final = (diversity + access + connectivity + infra + green + commercial_score) / NUM_SUBSCALES
    return round(min(max(final, 0), 100), 1)


def run(neighborhood_name: str | None = None):
    if not GOOGLE_MAPS_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not set")
        return

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            if neighborhood_name:
                cur.execute(
                    """SELECT id, name, ST_Y(center_geog::geometry), ST_X(center_geog::geometry)
                       FROM neighborhoods WHERE name = %s""",
                    (neighborhood_name,),
                )
            else:
                cur.execute(
                    """SELECT id, name, ST_Y(center_geog::geometry), ST_X(center_geog::geometry)
                       FROM neighborhoods ORDER BY name"""
                )
            rows = cur.fetchall()

            total = len(rows)
            print(f"Computing walkability for {total} neighborhoods (DB + Google Maps)...\n")

            for i, (nid, name, lat, lon) in enumerate(rows, 1):
                print(f"  [{i}/{total}] {name}...", end=" ", flush=True)

                # Step 1: Count facilities from our DB
                db_data = _count_db_facilities(cur, lat, lon)

                # Step 2: Fetch amenities from Google Maps Places API
                amenities = {}
                for place_type in ["grocery_or_supermarket", "restaurant", "pharmacy", "park"]:
                    amenities[place_type] = _fetch_google_places(lat, lon, place_type)
                    time.sleep(0.05)

                # Store amenity counts
                cur.execute(
                    """INSERT INTO neighborhood_amenities
                       (neighborhood_id, grocery_count_1km, restaurant_count_1km, pharmacy_count_1km, park_count_1km, fetched_at, source)
                       VALUES (%s, %s, %s, %s, %s, now(), 'google_maps')
                       ON CONFLICT (neighborhood_id) DO UPDATE SET
                         grocery_count_1km = EXCLUDED.grocery_count_1km,
                         restaurant_count_1km = EXCLUDED.restaurant_count_1km,
                         pharmacy_count_1km = EXCLUDED.pharmacy_count_1km,
                         park_count_1km = EXCLUDED.park_count_1km,
                         fetched_at = now()""",
                    (nid, amenities.get("grocery_or_supermarket", 0),
                     amenities.get("restaurant", 0),
                     amenities.get("pharmacy", 0),
                     amenities.get("park", 0)),
                )

                # Step 3: Compute score
                score = _compute_score(db_data, amenities)

                # Step 4: Update walkability_zones
                cur.execute(
                    "UPDATE walkability_zones SET score = %s WHERE neighborhood_id = %s",
                    (score, nid),
                )
                if cur.rowcount == 0:
                    cur.execute(
                        """INSERT INTO walkability_zones (neighborhood_id, area, score, center_geog, radius_km)
                           VALUES (%s, %s, %s, ST_Point(%s, %s)::geography, 2.0)""",
                        (nid, name, score, lon, lat),
                    )

                conn.commit()

                db_total = sum(db_data["counts"].values())
                goog_total = sum(amenities.values())
                print(f"{score} (DB:{db_total} + Google:{goog_total} amenities)")

                time.sleep(0.2)

            print(f"\nDone: {total} walkability scores computed.")
    finally:
        conn.close()


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else None
    run(name)
