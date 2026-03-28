"""
Fetch Parks and Open Spaces data from data.opencity.in for Bengaluru.

Source:
  - Bengaluru Parks CSV — data.opencity.in (CC BY 4.0)
  - BBMP Parks and Playgrounds data

Downloads park locations, seeds them into the DB for use by the
walkability scorer as a green space access sub-score.
"""

import csv
import io
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import BANGALORE_BBOX, CURATED_DIR
from app.db import get_sync_conn

PARKS_CSV_URL = "https://data.opencity.in/dataset/bengaluru-parks/resource/download"


def fetch():
    print("  Downloading Bengaluru Parks data from data.opencity.in...")

    try:
        req = urllib.request.Request(
            PARKS_CSV_URL,
            headers={"User-Agent": "bangalore-score/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read().decode("utf-8-sig")
    except Exception as e:
        print(f"  Warning: Could not fetch parks CSV ({e})")
        return 0

    reader = csv.DictReader(io.StringIO(raw))
    parks = []

    for row in reader:
        name = (
            row.get("Park Name", "") or row.get("park_name", "") or row.get("Name", "") or row.get("name", "")
        ).strip()

        lat_str = row.get("Latitude", row.get("latitude", row.get("lat", "")))
        lon_str = row.get("Longitude", row.get("longitude", row.get("lon", row.get("lng", ""))))

        if not name or not lat_str or not lon_str:
            continue

        try:
            lat = float(lat_str)
            lon = float(lon_str)
        except ValueError:
            continue

        if not (
            BANGALORE_BBOX["south"] <= lat <= BANGALORE_BBOX["north"]
            and BANGALORE_BBOX["west"] <= lon <= BANGALORE_BBOX["east"]
        ):
            continue

        area_sqm = None
        area_str = row.get("Area_sqm", row.get("area", row.get("Area", "")))
        if area_str:
            try:
                area_sqm = float(area_str)
            except ValueError:
                pass

        ward = (row.get("Ward", "") or row.get("ward", "")).strip() or None

        parks.append(
            {
                "name": name,
                "latitude": lat,
                "longitude": lon,
                "area_sqm": area_sqm,
                "ward": ward,
            }
        )

    if not parks:
        print("  No valid parks parsed from CSV. Data format may have changed.")
        return 0

    # Save as JSON reference
    output = {
        "source": "Bengaluru Parks — data.opencity.in (CC BY 4.0)",
        "fetched": "2026-03",
        "total_parks": len(parks),
        "parks": parks,
    }

    out_path = CURATED_DIR / "parks.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  Parsed {len(parks)} parks from CSV")

    # Seed into DB
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS parks (
                    id       SERIAL PRIMARY KEY,
                    name     TEXT NOT NULL,
                    area_sqm REAL,
                    ward     TEXT,
                    geog     GEOGRAPHY(Point, 4326) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            cur.execute("DELETE FROM parks")
            for p in parks:
                cur.execute(
                    """INSERT INTO parks (name, area_sqm, ward, geog)
                       VALUES (%s, %s, %s, ST_Point(%s, %s)::geography)""",
                    (p["name"], p.get("area_sqm"), p.get("ward"), p["longitude"], p["latitude"]),
                )
        conn.commit()
        print(f"  OK: {len(parks)} parks seeded into DB")
    finally:
        conn.close()

    return len(parks)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
