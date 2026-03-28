"""
Derive canonical neighborhoods from all curated JSON files.
Uses property_prices.json as the primary source (most complete),
then fills in any areas found in other zone files but missing from prices.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn

ZONE_FILES_WITH_AREA = [
    ("property_prices.json", "areas", "area", "center_lat", "center_lon", "radius_km"),
    ("walkability_zones.json", "zones", "area", "center_lat", "center_lon", "radius_km"),
    ("water_zones.json", "zones", "area", "center_lat", "center_lon", "radius_km"),
    ("power_zones.json", "zones", "area", "center_lat", "center_lon", "radius_km"),
    ("business_opportunity.json", "zones", "area", "center_lat", "center_lon", "radius_km"),
    ("safety_zones.json", "zones", "zone", "center_lat", "center_lon", "radius_km"),
]


# Legacy compass labels (older safety_zones.json); current file uses neighborhood names only
SKIP_ZONES = {"Central", "East", "West", "South", "North", "South-East", "North-East"}


def _load_areas() -> dict[str, dict]:
    """Collect unique areas with coordinates from all zone JSON files."""
    areas: dict[str, dict] = {}

    for filename, list_key, name_key, lat_key, lon_key, radius_key in ZONE_FILES_WITH_AREA:
        path = CURATED_DIR / filename
        if not path.exists():
            continue
        with open(path) as f:
            data = json.load(f)
        for item in data.get(list_key, []):
            name = item[name_key]
            if name in SKIP_ZONES:
                continue
            if name not in areas:
                areas[name] = {
                    "name": name,
                    "lat": item[lat_key],
                    "lon": item[lon_key],
                    "radius_km": item.get(radius_key, 2.0),
                }
    return areas


def seed():
    areas = _load_areas()
    print(f"  Neighborhoods: {len(areas)} unique areas found across JSON files")

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM noise_zones")
            cur.execute("DELETE FROM delivery_coverage")
            cur.execute("DELETE FROM commute_times")
            cur.execute("DELETE FROM flood_risk")
            cur.execute("DELETE FROM business_opportunity")
            cur.execute("DELETE FROM property_prices")
            cur.execute("DELETE FROM walkability_zones")
            cur.execute("DELETE FROM power_zones")
            cur.execute("DELETE FROM water_zones")
            cur.execute("DELETE FROM safety_zones")
            cur.execute("DELETE FROM neighborhoods")

            for area in areas.values():
                cur.execute(
                    """INSERT INTO neighborhoods (name, center_geog, radius_km)
                       VALUES (%s, ST_Point(%s, %s)::geography, %s)
                       ON CONFLICT (name) DO UPDATE SET
                         center_geog = EXCLUDED.center_geog,
                         radius_km = EXCLUDED.radius_km""",
                    (area["name"], area["lon"], area["lat"], area["radius_km"]),
                )
        conn.commit()
        print(f"  OK: {len(areas)} neighborhoods seeded")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
