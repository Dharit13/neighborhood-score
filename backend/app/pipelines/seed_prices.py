"""
Seed property prices, builders, and business opportunity from curated JSON files.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn


def _get_neighborhood_map(cur) -> dict[str, int]:
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

            # --- Property prices ---
            cur.execute("DELETE FROM property_prices")
            with open(CURATED_DIR / "property_prices.json") as f:
                data = json.load(f)
            count = 0
            for a in data["areas"]:
                nid = _find_neighborhood_id(a["area"], nmap)
                cur.execute(
                    """INSERT INTO property_prices
                       (neighborhood_id, area, avg_price_sqft, price_range_low, price_range_high,
                        avg_2bhk_lakh, avg_3bhk_lakh, avg_2bhk_rent, avg_3bhk_rent,
                        yoy_growth_pct, rental_yield_pct, emi_to_income_pct,
                        affordability_score, affordability_label, center_geog, radius_km,
                        avg_maintenance_monthly, resale_avg_days_on_market)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               ST_Point(%s, %s)::geography, %s, %s, %s)""",
                    (
                        nid, a["area"], a["avg_price_sqft"],
                        a["price_range_low"], a["price_range_high"],
                        a["avg_2bhk_lakh"], a["avg_3bhk_lakh"],
                        a["avg_2bhk_rent"], a["avg_3bhk_rent"],
                        a["yoy_growth_pct"], a["rental_yield_pct"],
                        a["emi_to_income_pct"], a["affordability_score"],
                        a["affordability_label"],
                        a["center_lon"], a["center_lat"], a["radius_km"],
                        a.get("avg_maintenance_monthly"), a.get("resale_avg_days_on_market"),
                    ),
                )
                count += 1
            print(f"  Property prices: {count} areas seeded")

            # --- Builders ---
            cur.execute("DELETE FROM builders")
            with open(CURATED_DIR / "builders.json") as f:
                data = json.load(f)
            count = 0
            for b in data["builders"]:
                cur.execute(
                    """INSERT INTO builders
                       (name, rera_projects, total_projects_blr, complaints, complaints_ratio,
                        on_time_delivery_pct, avg_rating, reputation_tier, active_areas, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (name) DO UPDATE SET
                         rera_projects = EXCLUDED.rera_projects,
                         score = EXCLUDED.score""",
                    (
                        b["name"], b["rera_projects"], b["total_projects_blr"],
                        b["complaints"], b["complaints_ratio"],
                        b["on_time_delivery_pct"], b["avg_rating"],
                        b["reputation_tier"], b["active_areas"], b["score"],
                    ),
                )
                count += 1
            print(f"  Builders: {count} seeded")

            # --- Business opportunity ---
            cur.execute("DELETE FROM business_opportunity")
            with open(CURATED_DIR / "business_opportunity.json") as f:
                data = json.load(f)
            count = 0
            for z in data["zones"]:
                nid = _find_neighborhood_id(z["area"], nmap)
                cur.execute(
                    """INSERT INTO business_opportunity
                       (neighborhood_id, area, new_business_acceptability_pct, commercial_rent_sqft,
                        footfall_index, startup_density, coworking_spaces, consumer_spending_index,
                        business_type_fit, score, label, center_geog, radius_km)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                               ST_Point(%s, %s)::geography, %s)""",
                    (
                        nid, z["area"], z["new_business_acceptability_pct"],
                        z["commercial_rent_sqft"], z["footfall_index"],
                        z["startup_density"], z["coworking_spaces"],
                        z["consumer_spending_index"], z["business_type_fit"],
                        z["score"], z["label"],
                        z["center_lon"], z["center_lat"], z["radius_km"],
                    ),
                )
                count += 1
            print(f"  Business opportunity: {count} zones seeded")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
