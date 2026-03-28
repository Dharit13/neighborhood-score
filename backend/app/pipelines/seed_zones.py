"""
Seed safety, water, power, walkability zones from curated JSON files.
Links each zone to its matching neighborhood row via name lookup.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn


def _get_neighborhood_map(cur) -> dict[str, int]:
    """Build name→id map for neighborhoods."""
    cur.execute("SELECT id, name FROM neighborhoods")
    return {row[1]: row[0] for row in cur.fetchall()}


def _find_neighborhood_id(name: str, nmap: dict[str, int]) -> int | None:
    if name in nmap:
        return nmap[name]
    name_lower = name.lower()
    for n, nid in nmap.items():
        if n.lower() == name_lower or name_lower in n.lower() or n.lower() in name_lower:
            return nid
    return None


def seed():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            nmap = _get_neighborhood_map(cur)

            # --- Safety zones ---
            cur.execute("DELETE FROM safety_zones")
            with open(CURATED_DIR / "safety_zones.json") as f:
                data = json.load(f)
            count = 0
            for z in data["zones"]:
                nid = _find_neighborhood_id(z["zone"], nmap)
                cur.execute(
                    """INSERT INTO safety_zones
                       (neighborhood_id, zone_name, crime_rate_per_100k, streetlight_pct,
                        cctv_density_per_sqkm, police_density_per_sqkm, score, center_geog, radius_km)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, ST_Point(%s, %s)::geography, %s)""",
                    (
                        nid,
                        z["zone"],
                        z["crime_rate_per_100k"],
                        z["streetlight_pct"],
                        z["cctv_density_per_sqkm"],
                        z["police_density_per_sqkm"],
                        z.get("score"),
                        z["center_lon"],
                        z["center_lat"],
                        z["radius_km"],
                    ),
                )
                count += 1
            print(f"  Safety zones: {count} seeded")

            # --- Water zones ---
            cur.execute("DELETE FROM water_zones")
            with open(CURATED_DIR / "water_zones.json") as f:
                data = json.load(f)
            count = 0
            for z in data["zones"]:
                nid = _find_neighborhood_id(z["area"], nmap)
                cur.execute(
                    """INSERT INTO water_zones
                       (neighborhood_id, area, stage, supply_hours, reliability, score, center_geog, radius_km)
                       VALUES (%s, %s, %s, %s, %s, %s, ST_Point(%s, %s)::geography, %s)""",
                    (
                        nid,
                        z["area"],
                        z["stage"],
                        z["supply_hours_per_day"],
                        z["reliability"],
                        z["score"],
                        z["center_lon"],
                        z["center_lat"],
                        z["radius_km"],
                    ),
                )
                count += 1
            print(f"  Water zones: {count} seeded")

            # --- Power zones ---
            cur.execute("DELETE FROM power_zones")
            with open(CURATED_DIR / "power_zones.json") as f:
                data = json.load(f)
            count = 0
            for z in data["zones"]:
                nid = _find_neighborhood_id(z["area"], nmap)
                cur.execute(
                    """INSERT INTO power_zones
                       (neighborhood_id, area, tier, avg_monthly_outage_hours, score, center_geog, radius_km)
                       VALUES (%s, %s, %s, %s, %s, ST_Point(%s, %s)::geography, %s)""",
                    (
                        nid,
                        z["area"],
                        z["tier"],
                        z["avg_monthly_outage_hours"],
                        z["score"],
                        z["center_lon"],
                        z["center_lat"],
                        z["radius_km"],
                    ),
                )
                count += 1
            print(f"  Power zones: {count} seeded")

            # --- Walkability zones ---
            cur.execute("DELETE FROM walkability_zones")
            with open(CURATED_DIR / "walkability_zones.json") as f:
                data = json.load(f)
            count = 0
            for z in data["zones"]:
                nid = _find_neighborhood_id(z["area"], nmap)
                cur.execute(
                    """INSERT INTO walkability_zones
                       (neighborhood_id, area, score, center_geog, radius_km)
                       VALUES (%s, %s, %s, ST_Point(%s, %s)::geography, %s)""",
                    (
                        nid,
                        z["area"],
                        z["score"],
                        z["center_lon"],
                        z["center_lat"],
                        z["radius_km"],
                    ),
                )
                count += 1
            print(f"  Walkability zones: {count} seeded")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
