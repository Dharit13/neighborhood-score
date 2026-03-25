"""
Seed metro stations, bus stops, train stations from curated JSON files.
Also seeds tech_parks (referenced by commute_times).
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn

TECH_PARKS = [
    {"name": "Manyata Tech Park", "lat": 13.0474, "lon": 77.6217, "company_count": 60, "employee_estimate": 50000},
    {"name": "Embassy Tech Village", "lat": 12.9249, "lon": 77.6779, "company_count": 40, "employee_estimate": 40000},
    {"name": "RMZ Ecospace", "lat": 12.9266, "lon": 77.6846, "company_count": 30, "employee_estimate": 30000},
    {"name": "Bagmane Tech Park", "lat": 12.9694, "lon": 77.6483, "company_count": 25, "employee_estimate": 25000},
    {"name": "ITPL (International Tech Park)", "lat": 12.9856, "lon": 77.7319, "company_count": 80, "employee_estimate": 45000},
    {"name": "Embassy TechVillage Outer Ring Road", "lat": 12.9321, "lon": 77.6901, "company_count": 35, "employee_estimate": 35000},
    {"name": "Prestige Tech Park", "lat": 12.9335, "lon": 77.6102, "company_count": 20, "employee_estimate": 20000},
    {"name": "Brigade Gateway / WTC", "lat": 12.9959, "lon": 77.5546, "company_count": 15, "employee_estimate": 10000},
    {"name": "Cessna Business Park", "lat": 12.9350, "lon": 77.6806, "company_count": 20, "employee_estimate": 15000},
    {"name": "Electronic City Phase 1 & 2", "lat": 12.8450, "lon": 77.6600, "company_count": 150, "employee_estimate": 100000},
]


def seed():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            # --- Metro stations ---
            cur.execute("DELETE FROM metro_stations")
            with open(CURATED_DIR / "metro_stations.json") as f:
                data = json.load(f)
            for s in data["stations"]:
                status = s.get("status", "operational")
                cur.execute(
                    """INSERT INTO metro_stations (name, line, geog, status)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography, %s)""",
                    (s["name"], s["line"], s["longitude"], s["latitude"], status),
                )
            operational = sum(1 for s in data["stations"] if s.get("status", "operational") == "operational")
            construction = sum(1 for s in data["stations"] if s.get("status") == "construction")
            print(f"  Metro stations: {len(data['stations'])} seeded ({operational} operational, {construction} under construction)")

            # --- Bus stops ---
            cur.execute("DELETE FROM bus_stops")
            with open(CURATED_DIR / "bus_stops.json") as f:
                data = json.load(f)
            for s in data["stops"]:
                cur.execute(
                    """INSERT INTO bus_stops (name, ward, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (s["name"], s.get("ward"), s["longitude"], s["latitude"]),
                )
            print(f"  Bus stops: {len(data['stops'])} seeded")

            # --- Train stations ---
            cur.execute("DELETE FROM train_stations")
            with open(CURATED_DIR / "train_stations.json") as f:
                data = json.load(f)
            for s in data["stations"]:
                cur.execute(
                    """INSERT INTO train_stations (name, type, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (s["name"], s["type"], s["longitude"], s["latitude"]),
                )
            print(f"  Train stations: {len(data['stations'])} seeded")

            # --- Tech parks ---
            cur.execute("DELETE FROM commute_times")
            cur.execute("DELETE FROM tech_parks")
            for tp in TECH_PARKS:
                cur.execute(
                    """INSERT INTO tech_parks (name, geog, company_count, employee_estimate)
                       VALUES (%s, ST_Point(%s, %s)::geography, %s, %s)""",
                    (tp["name"], tp["lon"], tp["lat"], tp["company_count"], tp["employee_estimate"]),
                )
            print(f"  Tech parks: {len(TECH_PARKS)} seeded")

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
