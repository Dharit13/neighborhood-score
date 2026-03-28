"""
Bulk Google Places pipeline — populates the unified `pois` table.

Grid-based Nearby Search across Bangalore, deduplicates by place_id,
then merges curated metadata (ranked schools, NABH hospitals, metro lines)
into the tags JSONB column.

Usage:
    python -m app.pipelines.fetch_google_places          # full run
    python -m app.pipelines.fetch_google_places --dry-run # grid preview only
"""

import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import httpx

from app.config import CURATED_DIR, GOOGLE_MAPS_API_KEY
from app.db import get_sync_conn, run_sql_file

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PLACE_TYPES = {
    "school": ["school", "university"],
    "hospital": ["hospital"],
    "police": ["police"],
    "transit_station": ["transit_station"],
    "bus_station": ["bus_station"],
    "park": ["park"],
    "supermarket": ["supermarket"],
    "pharmacy": ["pharmacy"],
}

# Bangalore metro bounding box
LAT_MIN, LAT_MAX = 12.75, 13.15
LON_MIN, LON_MAX = 77.45, 77.80

GRID_SPACING_KM = 4.0
SEARCH_RADIUS_M = 3000

KM_PER_DEG_LAT = 111.32
KM_PER_DEG_LON_AT_13 = 111.32 * math.cos(math.radians(13.0))


def generate_grid():
    """Generate a regular lat/lon grid covering Bangalore."""
    lat_step = GRID_SPACING_KM / KM_PER_DEG_LAT
    lon_step = GRID_SPACING_KM / KM_PER_DEG_LON_AT_13

    points = []
    lat = LAT_MIN
    while lat <= LAT_MAX:
        lon = LON_MIN
        while lon <= LON_MAX:
            points.append((round(lat, 5), round(lon, 5)))
            lon += lon_step
        lat += lat_step
    return points


def fetch_nearby(client: httpx.Client, lat: float, lon: float, place_type: str) -> list[dict]:
    """Fetch up to 60 results for one (lat, lon, type) using pagination."""
    results = []
    params = {
        "location": f"{lat},{lon}",
        "radius": SEARCH_RADIUS_M,
        "type": place_type,
        "key": GOOGLE_MAPS_API_KEY,
    }

    for page in range(3):  # max 3 pages of 20
        resp = client.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params=params,
        )
        data = resp.json()
        if data.get("status") not in ("OK", "ZERO_RESULTS"):
            print(f"    API error: {data.get('status')} — {data.get('error_message', '')}")
            break

        for place in data.get("results", []):
            loc = place.get("geometry", {}).get("location", {})
            results.append(
                {
                    "place_id": place["place_id"],
                    "name": place["name"],
                    "lat": loc.get("lat"),
                    "lng": loc.get("lng"),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                }
            )

        npt = data.get("next_page_token")
        if not npt:
            break
        params = {"pagetoken": npt, "key": GOOGLE_MAPS_API_KEY}
        time.sleep(2)  # Google requires ~2s before next_page_token is valid

    return results


def load_curated_schools() -> dict[str, dict]:
    """Load curated school data keyed by lowercase name for fuzzy matching."""
    path = CURATED_DIR / "top_schools.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    lookup = {}
    for s in data.get("schools", []):
        key = s["name"].lower().strip()
        lookup[key] = {
            "rank": s.get("rank"),
            "board": s.get("board"),
            "fee_range": s.get("fee_range_lakh_pa"),
            "admission_difficulty": s.get("admission_difficulty"),
            "source": "IIRF 2024",
        }
    return lookup


def load_curated_hospitals() -> dict[str, dict]:
    """Load curated hospital data keyed by lowercase name."""
    path = CURATED_DIR / "nabh_hospitals.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    lookup = {}
    for h in data.get("hospitals", []):
        key = h["name"].lower().strip()
        lookup[key] = {
            "accreditation": h.get("accreditation"),
            "tier": h.get("tier"),
            "beds": h.get("beds"),
            "specialties": h.get("specialties", []),
        }
    return lookup


def load_curated_metro() -> dict[str, dict]:
    """Load curated metro station data keyed by lowercase name."""
    path = CURATED_DIR / "metro_stations.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    lookup = {}
    for s in data.get("stations", []):
        key = s["name"].lower().strip()
        lookup[key] = {
            "line": s.get("line"),
            "status": s.get("status", "operational"),
            "source": "CityLines",
        }
    return lookup


def match_curated(name: str, lookup: dict[str, dict]) -> dict:
    """Try exact then substring match against curated lookup.
    Requires the shorter string to be at least 60% of the longer to avoid
    false positives like 'School' matching every school name."""
    key = name.lower().strip()
    if len(key) < 8:
        return {}
    if key in lookup:
        return lookup[key]
    for curated_name, tags in lookup.items():
        shorter, longer = (key, curated_name) if len(key) <= len(curated_name) else (curated_name, key)
        if len(shorter) / max(len(longer), 1) < 0.4:
            continue
        if shorter in longer:
            return tags
    return {}


def upsert_pois(pois: list[dict]):
    """Bulk upsert into the pois table."""
    if not pois:
        return

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            for poi in pois:
                cur.execute(
                    """INSERT INTO pois (place_id, name, category, geog, rating, user_ratings_total, tags)
                       VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s, %s, %s::jsonb)
                       ON CONFLICT (place_id) DO UPDATE SET
                         name = EXCLUDED.name,
                         rating = EXCLUDED.rating,
                         user_ratings_total = EXCLUDED.user_ratings_total,
                         tags = pois.tags || EXCLUDED.tags""",
                    (
                        poi["place_id"],
                        poi["name"],
                        poi["category"],
                        poi["lng"],
                        poi["lat"],
                        poi["rating"],
                        poi["user_ratings_total"],
                        json.dumps(poi.get("tags", {})),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def fetch():
    """Main pipeline entry point."""
    if not GOOGLE_MAPS_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not set. Skipping Google Places fetch.")
        return

    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
    migration_path = os.path.join(migrations_dir, "005_google_places.sql")
    if os.path.exists(migration_path):
        print("  Running 005_google_places.sql migration...")
        run_sql_file(migration_path)

    grid = generate_grid()
    print(f"  Grid: {len(grid)} points, {SEARCH_RADIUS_M}m radius, {GRID_SPACING_KM}km spacing")

    # Load curated data for tag merging
    school_lookup = load_curated_schools()
    hospital_lookup = load_curated_hospitals()
    metro_lookup = load_curated_metro()
    print(
        f"  Curated data: {len(school_lookup)} schools, {len(hospital_lookup)} hospitals, {len(metro_lookup)} metro stations"
    )

    # Deduplicate globally by place_id
    seen: dict[str, dict] = {}
    api_calls = 0
    total_types = sum(len(types) for types in PLACE_TYPES.values())
    total_expected = len(grid) * total_types

    print(f"  Expected API calls: ~{total_expected}")
    print()

    with httpx.Client(timeout=10.0) as client:
        for gi, (lat, lon) in enumerate(grid):
            for category, google_types in PLACE_TYPES.items():
                for gtype in google_types:
                    api_calls += 1
                    if api_calls % 50 == 0 or api_calls == 1:
                        print(f"  [{api_calls}/{total_expected}] grid {gi + 1}/{len(grid)}: {gtype} @ ({lat}, {lon})")

                    try:
                        results = fetch_nearby(client, lat, lon, gtype)
                    except Exception as e:
                        print(f"    Error: {e}")
                        continue

                    for r in results:
                        pid = r["place_id"]
                        if pid in seen:
                            continue

                        tags = {}
                        if category in ("school",):
                            tags = match_curated(r["name"], school_lookup)
                        elif category == "hospital":
                            tags = match_curated(r["name"], hospital_lookup)
                        elif category == "transit_station":
                            tags = match_curated(r["name"], metro_lookup)

                        seen[pid] = {
                            **r,
                            "category": category,
                            "tags": tags,
                        }

    print(f"\n  Total API calls: {api_calls}")
    print(f"  Unique POIs found: {len(seen)}")

    # Category breakdown
    cats = {}
    for poi in seen.values():
        cats[poi["category"]] = cats.get(poi["category"], 0) + 1
    for cat, count in sorted(cats.items()):
        tagged = sum(1 for p in seen.values() if p["category"] == cat and p.get("tags"))
        print(f"    {cat}: {count} ({tagged} with curated tags)")

    # Upsert in batches
    all_pois = list(seen.values())
    batch_size = 200
    for i in range(0, len(all_pois), batch_size):
        batch = all_pois[i : i + batch_size]
        upsert_pois(batch)
        print(f"  Upserted batch {i // batch_size + 1}/{math.ceil(len(all_pois) / batch_size)}")

    print(f"  Done — {len(all_pois)} POIs in pois table.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Only show grid, don't call API")
    args = parser.parse_args()

    if args.dry_run:
        grid = generate_grid()
        total_types = sum(len(types) for types in PLACE_TYPES.values())
        print(f"Grid: {len(grid)} points")
        print(f"Types per point: {total_types}")
        print(f"Expected API calls: {len(grid) * total_types}")
        print(f"Estimated cost: ~${len(grid) * total_types * 0.032:.2f}")
        for i, (lat, lon) in enumerate(grid[:5]):
            print(f"  Sample point {i + 1}: ({lat}, {lon})")
        print(f"  ... and {len(grid) - 5} more")
    else:
        fetch()
