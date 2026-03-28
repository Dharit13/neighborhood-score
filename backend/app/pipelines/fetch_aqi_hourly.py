"""
Fetch Hourly AQI data from data.opencity.in for Bengaluru.

Source:
  - Bengaluru Hourly Air Quality Reports — data.opencity.in (CC BY 4.0)
  - CPCB continuous monitoring station data

Downloads hourly AQI CSV, computes per-station time-of-day averages
(morning rush, midday, evening rush, night), and saves as reference
data for the air quality scorer.
"""

import csv
import io
import json
import os
import sys
import urllib.request
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import CURATED_DIR

AQI_HOURLY_CSV_URL = "https://data.opencity.in/dataset/bengaluru-hourly-air-quality/resource/download"


def _time_period(hour: int) -> str:
    if 6 <= hour < 10:
        return "morning_rush"
    elif 10 <= hour < 16:
        return "midday"
    elif 16 <= hour < 21:
        return "evening_rush"
    else:
        return "night"


def fetch():
    print("  Downloading Bengaluru Hourly AQI data from data.opencity.in...")

    try:
        req = urllib.request.Request(
            AQI_HOURLY_CSV_URL,
            headers={"User-Agent": "bangalore-score/1.0"},
        )
        resp = urllib.request.urlopen(req, timeout=60)
        raw = resp.read().decode("utf-8-sig")
    except Exception as e:
        print(f"  Warning: Could not fetch hourly AQI CSV ({e})")
        print("  Falling back to existing aqi_stations.json data.")
        return 0

    reader = csv.DictReader(io.StringIO(raw))

    # station -> period -> [aqi values]
    station_period_aqi: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    station_overall: dict[str, list[float]] = defaultdict(list)
    rows_parsed = 0

    for row in reader:
        station = (row.get("Station", "") or row.get("station", "") or row.get("Station Name", "")).strip()
        if not station:
            continue

        aqi_val = row.get("AQI", row.get("aqi", ""))
        hour_val = row.get("Hour", row.get("hour", ""))

        try:
            aqi = float(aqi_val)
            hour = int(hour_val)
        except (ValueError, TypeError):
            continue

        if aqi <= 0 or aqi > 500:
            continue

        period = _time_period(hour)
        station_period_aqi[station][period].append(aqi)
        station_overall[station].append(aqi)
        rows_parsed += 1

    if not station_period_aqi:
        print("  No valid hourly AQI rows parsed. Data format may have changed.")
        return 0

    stations_summary = {}
    for station, periods in station_period_aqi.items():
        summary = {}
        for period, values in periods.items():
            summary[period] = round(sum(values) / len(values), 1)
        overall = station_overall[station]
        summary["daily_avg"] = round(sum(overall) / len(overall), 1)
        summary["readings_count"] = len(overall)
        stations_summary[station] = summary

    output = {
        "source": "Bengaluru Hourly Air Quality Reports — data.opencity.in (CC BY 4.0)",
        "fetched": "2026-03",
        "methodology": "Hourly AQI readings averaged by time-of-day period: morning_rush (6-10), midday (10-16), evening_rush (16-21), night (21-6)",
        "total_readings_parsed": rows_parsed,
        "stations": stations_summary,
    }

    out_path = CURATED_DIR / "aqi_hourly.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"  OK: {rows_parsed} hourly readings from {len(stations_summary)} stations")
    print(f"  Saved to {out_path}")

    return rows_parsed


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
