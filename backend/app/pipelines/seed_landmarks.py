"""
Seed landmark_registry from:
  1. Curated landmarks.json (tech parks, junctions, areas, airport, etc.)
  2. Existing metro_stations table (with auto-generated aliases)
  3. Existing tech_parks table (merged with curated to avoid duplicates)
"""

import json
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _metro_aliases(name: str) -> list[str]:
    """Generate common aliases for metro station names."""
    aliases = []

    # "Mahatma Gandhi Road (MG Road)" -> aliases: MG Road, Mahatma Gandhi Road
    paren_match = re.search(r'\(([^)]+)\)', name)
    if paren_match:
        inner = paren_match.group(1)
        outer = re.sub(r'\s*\([^)]+\)\s*', '', name).strip()
        aliases.extend([inner, outer])

    # "Halasuru (Ulsoor)" -> Ulsoor, Halasuru
    # Already handled above

    # "City Railway Station (Majestic)" -> Majestic
    # Already handled

    # Common suffix removal: " Metro", " Metro Station"
    for suffix in [" Metro Station", " Metro", " Station"]:
        if name.endswith(suffix):
            aliases.append(name[:-len(suffix)])

    # Add "X Metro" variant
    clean = re.sub(r'\s*\([^)]+\)\s*', '', name).strip()
    aliases.append(f"{clean} Metro")
    aliases.append(f"{clean} Metro Station")

    return list(set(a for a in aliases if a != name and len(a) > 1))


def seed():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM landmark_registry")

            inserted = 0

            # 1. Load curated landmarks
            with open(CURATED_DIR / "landmarks.json") as f:
                data = json.load(f)

            for lm in data["landmarks"]:
                cur.execute(
                    """INSERT INTO landmark_registry
                       (name, aliases, category, latitude, longitude, line, status, notes)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        lm["name"],
                        lm.get("aliases", []),
                        lm["category"],
                        lm["latitude"],
                        lm["longitude"],
                        lm.get("line"),
                        lm.get("status", "operational"),
                        lm.get("notes"),
                    ),
                )
                inserted += 1

            print(f"  Curated landmarks: {inserted} inserted")

            # 2. Import metro stations (from metro_stations table, already seeded)
            cur.execute(
                """SELECT name, line,
                          ST_Y(geog::geometry) as lat,
                          ST_X(geog::geometry) as lon,
                          status
                   FROM metro_stations"""
            )
            metro_rows = cur.fetchall()
            metro_count = 0

            # Track curated landmark names to avoid duplicates
            curated_names = set()
            for lm in data["landmarks"]:
                curated_names.add(lm["name"].lower())
                for alias in lm.get("aliases", []):
                    curated_names.add(alias.lower())

            for row in metro_rows:
                name, line, lat, lon, status = row
                if name.lower() in curated_names:
                    continue

                aliases = _metro_aliases(name)
                line_label = f"{line}_line" if line and "_line" not in line else line

                cur.execute(
                    """INSERT INTO landmark_registry
                       (name, aliases, category, latitude, longitude, line, status)
                       VALUES (%s, %s, 'metro_station', %s, %s, %s, %s)""",
                    (name, aliases, lat, lon, line_label, status or "operational"),
                )
                metro_count += 1

            print(f"  Metro stations: {metro_count} imported")

            # 3. Import tech parks from DB that aren't in curated landmarks
            cur.execute(
                """SELECT name,
                          ST_Y(geog::geometry) as lat,
                          ST_X(geog::geometry) as lon
                   FROM tech_parks"""
            )
            tp_rows = cur.fetchall()
            tp_count = 0

            for row in tp_rows:
                name, lat, lon = row
                if name.lower() in curated_names:
                    continue
                # Check partial match
                skip = False
                for cn in curated_names:
                    if cn in name.lower() or name.lower() in cn:
                        skip = True
                        break
                if skip:
                    continue

                cur.execute(
                    """INSERT INTO landmark_registry
                       (name, aliases, category, latitude, longitude)
                       VALUES (%s, %s, 'tech_park', %s, %s)""",
                    (name, [], lat, lon),
                )
                tp_count += 1

            print(f"  Tech parks: {tp_count} imported")

        conn.commit()
        total = inserted + metro_count + tp_count
        print(f"  OK: {total} total landmarks in registry")
        return total
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    seed()
