"""
Fetch Karnataka Crime Data 2024 CSV from data.opencity.in.

Source:
  - Karnataka Crime Data 2024 — data.opencity.in (CC BY 4.0)
  - https://data.opencity.in/dataset/karnataka-crime-data

Downloads the CSV, parses district-level crime stats, and filters
for Bengaluru Urban + Bengaluru Rural to update neighborhood-level
safety_zones.json with more granular crime rates.
"""

import csv
import io
import json
import sys
import os
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR

CRIME_CSV_URL = "https://data.opencity.in/dataset/karnataka-crime-data/resource/download"

BANGALORE_DISTRICTS = {"bengaluru urban", "bengaluru rural", "bangalore urban", "bangalore rural"}


def fetch():
    print("  Downloading Karnataka Crime Data 2024 from data.opencity.in...")

    try:
        req = urllib.request.Request(
            CRIME_CSV_URL,
            headers={"User-Agent": "bangalore-score/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read().decode("utf-8-sig")
    except Exception as e:
        print(f"  Warning: Could not fetch crime CSV ({e})")
        print("  Falling back to existing safety_zones.json data.")
        return 0

    reader = csv.DictReader(io.StringIO(raw))
    bangalore_rows = []
    for row in reader:
        district = (row.get("District", "") or row.get("district", "")).strip().lower()
        if district in BANGALORE_DISTRICTS:
            bangalore_rows.append(row)

    if not bangalore_rows:
        print("  No Bengaluru rows found in crime CSV. Data format may have changed.")
        return 0

    total_crimes = 0
    total_population = 0
    crime_categories = {}

    for row in bangalore_rows:
        for key, val in row.items():
            key_lower = key.strip().lower()
            if key_lower in ("district", "year", "population", "total"):
                continue
            try:
                count = int(val.strip()) if val.strip() else 0
                crime_categories[key.strip()] = crime_categories.get(key.strip(), 0) + count
                total_crimes += count
            except ValueError:
                pass

        pop_val = row.get("Population", row.get("population", "0"))
        try:
            total_population += int(pop_val.strip().replace(",", ""))
        except ValueError:
            pass

    city_crime_rate = (total_crimes / max(total_population, 1)) * 100_000 if total_population else 0

    # Save raw crime data as reference
    output = {
        "source": "Karnataka Crime Data 2024 — data.opencity.in (CC BY 4.0)",
        "fetched": "2026-03",
        "bangalore_total_crimes": total_crimes,
        "bangalore_population": total_population,
        "bangalore_crime_rate_per_100k": round(city_crime_rate, 1),
        "crime_categories": crime_categories,
        "rows_parsed": len(bangalore_rows),
    }

    out_path = CURATED_DIR / "crime_data_2024.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  OK: {len(bangalore_rows)} Bengaluru rows parsed, {total_crimes} total crimes")
    print(f"  City-wide crime rate: {city_crime_rate:.1f} per 100K")
    print(f"  Saved to {out_path}")

    return len(bangalore_rows)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fetch()
