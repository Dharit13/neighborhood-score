"""
Seed the areas table from curated areas.json.

areas.json is derived from property_prices.json (126 Bangalore areas
with lat/lon, price, growth data) merged with landmarks.json area entries.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn


def seed():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM areas")

            with open(CURATED_DIR / "areas.json") as f:
                data = json.load(f)

            count = 0
            for a in data["areas"]:
                cur.execute(
                    """INSERT INTO areas
                       (name, slug, latitude, longitude,
                        avg_price_per_sqft, price_yoy_change_pct,
                        geog)
                       VALUES (%s, %s, %s, %s, %s, %s,
                               ST_Point(%s, %s)::geography)
                       ON CONFLICT (slug) DO UPDATE SET
                         avg_price_per_sqft = EXCLUDED.avg_price_per_sqft,
                         price_yoy_change_pct = EXCLUDED.price_yoy_change_pct,
                         data_last_refreshed = now()""",
                    (
                        a["name"],
                        a["slug"],
                        a["latitude"],
                        a["longitude"],
                        a.get("avg_price_per_sqft"),
                        a.get("price_yoy_change_pct"),
                        a["longitude"],
                        a["latitude"],
                    ),
                )
                count += 1

        conn.commit()
        print(f"  OK: {count} areas seeded")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    seed()
