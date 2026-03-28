"""
Pre-compute full API score responses for all neighborhoods.

Saves the complete NeighborhoodScoreResponse for each neighborhood so both
the map pins and sidebar can serve cached data instantly (<100ms).

Usage:
  1. Start the backend: uvicorn app.main:app --port 8000
  2. Run: python -m app.pipelines.precompute_scores

Saves progress after each neighborhood so it can be resumed if interrupted.
Takes ~15-30 minutes for ~130 neighborhoods (~13s each).
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR
from app.db import get_sync_conn

API_URL = "http://localhost:8000/api/scores"
OUTPUT_FILE = CURATED_DIR / "precomputed_scores.json"


def precompute():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, ST_Y(center_geog::geometry) as lat, ST_X(center_geog::geometry) as lon
                FROM neighborhoods
                WHERE center_geog IS NOT NULL
                ORDER BY name
            """)
            neighborhoods = cur.fetchall()
    finally:
        conn.close()

    print(f"Pre-computing full scores for {len(neighborhoods)} neighborhoods...")
    print(f"Output: {OUTPUT_FILE}")
    print()

    results: dict[str, dict] = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)
        for entry in existing.get("neighborhoods", []):
            results[entry["name"]] = entry
        print(f"  Loaded {len(results)} existing scores (will skip these)")

    total = len(neighborhoods)
    errors = []
    start_time = time.time()

    for i, (name, lat, lon) in enumerate(neighborhoods):
        if name in results:
            print(f"  [{i + 1}/{total}] {name}: cached ({results[name]['composite_score']})")
            continue

        try:
            payload = json.dumps(
                {
                    "address": f"{name}, Bangalore",
                    "latitude": lat,
                    "longitude": lon,
                }
            ).encode()

            req = urllib.request.Request(
                API_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read().decode())

            data["name"] = name
            results[name] = data

            elapsed = time.time() - start_time
            computed = sum(1 for j, (n, _, _) in enumerate(neighborhoods[: i + 1]) if n not in results or j == i)
            avg_per = elapsed / max(computed, 1)
            remaining_count = sum(1 for n, _, _ in neighborhoods[i + 1 :] if n not in results)
            remaining = avg_per * remaining_count

            print(
                f"  [{i + 1}/{total}] {name}: {data['composite_score']} ({data['composite_label']}) "
                f"[~{remaining / 60:.0f}m remaining]"
            )

            _save(results)

        except Exception as e:
            print(f"  [{i + 1}/{total}] {name}: ERROR - {e}")
            errors.append(name)

    _save(results)
    elapsed = time.time() - start_time
    print(f"\nDone: {len(results)} full score responses cached in {elapsed / 60:.1f} minutes")
    if errors:
        print(f"Errors ({len(errors)}): {', '.join(errors)}")


def _save(results: dict):
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count": len(results),
        "neighborhoods": list(results.values()),
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, separators=(",", ":"))


if __name__ == "__main__":
    precompute()
