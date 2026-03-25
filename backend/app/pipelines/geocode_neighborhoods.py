"""
Geocode all neighborhoods using Google Maps API and update DB with accurate coordinates.
Usage: python -m app.pipelines.geocode_neighborhoods
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


def geocode_via_google(name: str) -> tuple[float, float] | None:
    address = f"{name}, Bangalore, Karnataka, India"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": GOOGLE_MAPS_API_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    loc = data["results"][0]["geometry"]["location"]
                    return (loc["lat"], loc["lng"])
    except Exception as e:
        print(f"    Error: {e}")
    return None


def run():
    if not GOOGLE_MAPS_API_KEY:
        print("ERROR: GOOGLE_MAPS_API_KEY not set in .env")
        return

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name,
                          ST_Y(center_geog::geometry) as lat,
                          ST_X(center_geog::geometry) as lon
                   FROM neighborhoods ORDER BY name"""
            )
            rows = cur.fetchall()

            total = len(rows)
            updated = 0
            print(f"Geocoding {total} neighborhoods via Google Maps API...\n")

            for i, (nid, name, old_lat, old_lon) in enumerate(rows, 1):
                result = geocode_via_google(name)
                if result:
                    new_lat, new_lon = result
                    cur.execute(
                        """UPDATE neighborhoods
                           SET center_geog = ST_Point(%s, %s)::geography
                           WHERE id = %s""",
                        (new_lon, new_lat, nid),
                    )
                    moved_m = (
                        ((new_lat - old_lat) ** 2 + (new_lon - old_lon) ** 2) ** 0.5
                    ) * 111000
                    status = f"({new_lat:.4f}, {new_lon:.4f})"
                    if moved_m > 100:
                        status += f" [moved {moved_m:.0f}m]"
                    print(f"  [{i}/{total}] {name}: {status}")
                    updated += 1
                else:
                    print(f"  [{i}/{total}] {name}: FAILED — keeping existing coords")

                time.sleep(0.1)

            conn.commit()
            print(f"\nDone: {updated}/{total} neighborhoods updated with Google Maps coordinates.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
