"""
Seed curated data (ranked schools, NABH hospitals, metro stations) into the pois table.
Run BEFORE or AFTER fetch_google_places — curated entries use ON CONFLICT to merge tags.

Usage: python -m app.pipelines.seed_curated_pois
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn, run_sql_file


def _synthetic_place_id(prefix: str, name: str) -> str:
    """Generate a deterministic place_id for curated entries without a Google place_id."""
    h = hashlib.md5(name.encode()).hexdigest()[:16]
    return f"curated_{prefix}_{h}"


def seed():
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "supabase", "migrations")
    migration_path = os.path.join(migrations_dir, "005_google_places.sql")
    if os.path.exists(migration_path):
        run_sql_file(migration_path)

    conn = get_sync_conn()
    count = 0

    try:
        with conn.cursor() as cur:
            # --- Ranked schools ---
            schools_path = CURATED_DIR / "top_schools.json"
            if schools_path.exists():
                data = json.loads(schools_path.read_text())
                for s in data.get("schools", []):
                    pid = _synthetic_place_id("school", s["name"])
                    tags = {
                        "rank": s.get("rank"),
                        "board": s.get("board"),
                        "fee_range": s.get("fee_range_lakh_pa"),
                        "admission_difficulty": s.get("admission_difficulty"),
                        "admission_window": s.get("admission_window"),
                        "seats": s.get("seats"),
                        "area": s.get("area"),
                        "source": "IIRF 2024",
                    }
                    cur.execute(
                        """INSERT INTO pois (place_id, name, category, geog, tags)
                           VALUES (%s, %s, 'school', ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s::jsonb)
                           ON CONFLICT (place_id) DO UPDATE SET
                             tags = pois.tags || EXCLUDED.tags""",
                        (pid, s["name"], s["longitude"], s["latitude"], json.dumps(tags)),
                    )
                    count += 1
                print(f"  Schools: {count} curated entries")

            # --- NABH hospitals ---
            hosp_count = 0
            hospitals_path = CURATED_DIR / "nabh_hospitals.json"
            if hospitals_path.exists():
                data = json.loads(hospitals_path.read_text())
                for h in data.get("hospitals", []):
                    pid = _synthetic_place_id("hospital", h["name"])
                    tags = {
                        "accreditation": h.get("accreditation"),
                        "tier": h.get("tier"),
                        "beds": h.get("beds"),
                        "specialties": h.get("specialties", []),
                        "area": h.get("area"),
                    }
                    cur.execute(
                        """INSERT INTO pois (place_id, name, category, geog, tags)
                           VALUES (%s, %s, 'hospital', ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s::jsonb)
                           ON CONFLICT (place_id) DO UPDATE SET
                             tags = pois.tags || EXCLUDED.tags""",
                        (pid, h["name"], h["longitude"], h["latitude"], json.dumps(tags)),
                    )
                    hosp_count += 1
                print(f"  Hospitals: {hosp_count} curated entries")
                count += hosp_count

            # --- Metro stations ---
            metro_count = 0
            metro_path = CURATED_DIR / "metro_stations.json"
            if metro_path.exists():
                data = json.loads(metro_path.read_text())
                for s in data.get("stations", []):
                    pid = _synthetic_place_id("metro", s["name"])
                    tags = {
                        "line": s.get("line"),
                        "status": s.get("status", "operational"),
                        "source": "CityLines",
                    }
                    cur.execute(
                        """INSERT INTO pois (place_id, name, category, geog, tags)
                           VALUES (%s, %s, 'transit_station', ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s::jsonb)
                           ON CONFLICT (place_id) DO UPDATE SET
                             tags = pois.tags || EXCLUDED.tags""",
                        (pid, s["name"], s["longitude"], s["latitude"], json.dumps(tags)),
                    )
                    metro_count += 1
                print(f"  Metro stations: {metro_count} curated entries")
                count += metro_count

            # --- Police stations ---
            police_count = 0
            police_path = CURATED_DIR / "police_stations.json"
            if police_path.exists():
                data = json.loads(police_path.read_text())
                for p in data.get("stations", data.get("police_stations", [])):
                    pid = _synthetic_place_id("police", p["name"])
                    tags = {"type": p.get("type", "police_station")}
                    cur.execute(
                        """INSERT INTO pois (place_id, name, category, geog, tags)
                           VALUES (%s, %s, 'police', ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s::jsonb)
                           ON CONFLICT (place_id) DO UPDATE SET
                             tags = pois.tags || EXCLUDED.tags""",
                        (pid, p["name"], p["longitude"], p["latitude"], json.dumps(tags)),
                    )
                    police_count += 1
                print(f"  Police stations: {police_count} curated entries")
                count += police_count

        conn.commit()
        print(f"  Total curated POIs seeded: {count}")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
