"""
Seed hospitals, schools, police stations, AQI stations from curated JSON files.
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn


def seed():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            # --- Hospitals ---
            cur.execute("DELETE FROM hospitals")
            with open(CURATED_DIR / "nabh_hospitals.json") as f:
                data = json.load(f)
            for h in data["hospitals"]:
                cur.execute(
                    """INSERT INTO hospitals (name, accreditation, tier, specialties, beds, area, geog)
                       VALUES (%s, %s, %s, %s, %s, %s, ST_Point(%s, %s)::geography)""",
                    (
                        h["name"], h["accreditation"], h["tier"],
                        h.get("specialties", []), h.get("beds"),
                        h.get("area"), h["longitude"], h["latitude"],
                    ),
                )
            print(f"  Hospitals: {len(data['hospitals'])} seeded")

            # --- Schools ---
            cur.execute("DELETE FROM schools")
            with open(CURATED_DIR / "top_schools.json") as f:
                data = json.load(f)
            for s in data["schools"]:
                cur.execute(
                    """INSERT INTO schools (name, board, rank, rank_score, area, geog,
                                           fee_range_lakh_pa, seats, admission_difficulty, admission_window)
                       VALUES (%s, %s, %s, %s, %s, ST_Point(%s, %s)::geography, %s, %s, %s, %s)""",
                    (
                        s["name"], s["board"], s["rank"], s["rank_score"],
                        s.get("area"), s["longitude"], s["latitude"],
                        s.get("fee_range_lakh_pa"), s.get("seats"),
                        s.get("admission_difficulty"), s.get("admission_window"),
                    ),
                )
            print(f"  Schools: {len(data['schools'])} seeded")

            # --- Police stations ---
            cur.execute("DELETE FROM police_stations")
            with open(CURATED_DIR / "police_stations.json") as f:
                data = json.load(f)
            for p in data["stations"]:
                cur.execute(
                    """INSERT INTO police_stations (name, type, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (p["name"], p.get("type", "station"), p["longitude"], p["latitude"]),
                )
            print(f"  Police stations: {len(data['stations'])} seeded")

            # --- AQI stations ---
            cur.execute("DELETE FROM aqi_readings")
            cur.execute("DELETE FROM aqi_stations")
            with open(CURATED_DIR / "aqi_stations.json") as f:
                data = json.load(f)
            for a in data["stations"]:
                cur.execute(
                    """INSERT INTO aqi_stations (name, area, geog, avg_aqi, primary_pollutant)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography, %s, %s)""",
                    (
                        a["name"], a.get("area"),
                        a["longitude"], a["latitude"],
                        a["avg_aqi"], a.get("primary_pollutant"),
                    ),
                )
            print(f"  AQI stations: {len(data['stations'])} seeded")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
