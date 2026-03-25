"""
Seed future infrastructure projects and their stations from curated JSON.
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
            cur.execute("DELETE FROM future_infra_stations")
            cur.execute("DELETE FROM future_infra_projects")

            with open(CURATED_DIR / "future_infra.json") as f:
                data = json.load(f)

            for proj in data["projects"]:
                cur.execute(
                    """INSERT INTO future_infra_projects
                       (name, type, status, expected_completion, length_km, cost_crore, description)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)
                       RETURNING id""",
                    (
                        proj["name"], proj["type"], proj["status"],
                        proj.get("expected_completion"),
                        proj.get("length_km"), proj.get("cost_crore"),
                        proj.get("description"),
                    ),
                )
                project_id = cur.fetchone()[0]

                points = proj.get("stations", proj.get("key_points", []))
                for st in points:
                    cur.execute(
                        """INSERT INTO future_infra_stations (project_id, name, geog)
                           VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                        (project_id, st["name"], st["longitude"], st["latitude"]),
                    )

                print(f"  {proj['name']}: {len(points)} stations seeded")

        conn.commit()
        print(f"  OK: {len(data['projects'])} infra projects seeded")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
