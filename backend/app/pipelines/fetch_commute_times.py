"""
Fetch real commute times from Google Maps Distance Matrix API.

Source: Google Maps Distance Matrix API
  - 74 neighborhoods x 10 tech parks = 740 origin-destination pairs
  - 2 modes (car_peak at 9am, car_offpeak at 2pm)
  - bike and bus_metro estimated from car times

Cost: ~$10 total (Distance Matrix Advanced is $10/1000 elements)
"""

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import GOOGLE_MAPS_API_KEY
from app.db import get_sync_conn

DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# Batch size: API allows max 25 origins or 25 destinations per request
BATCH_SIZE = 10


def _call_distance_matrix(origins, destinations, departure_time=None):
    """Call Google Maps Distance Matrix API."""
    params = {
        "origins": "|".join(f"{lat},{lon}" for lat, lon in origins),
        "destinations": "|".join(f"{lat},{lon}" for lat, lon in destinations),
        "mode": "driving",
        "key": GOOGLE_MAPS_API_KEY,
        "units": "metric",
    }
    if departure_time:
        params["departure_time"] = str(departure_time)
        params["traffic_model"] = "best_guess"

    url = f"{DISTANCE_MATRIX_URL}?{urllib.parse.urlencode(params)}"
    resp = urllib.request.urlopen(url, timeout=30)
    return json.loads(resp.read().decode("utf-8"))


def fetch():
    if not GOOGLE_MAPS_API_KEY:
        print("  ERROR: GOOGLE_MAPS_API_KEY not set. Cannot fetch commute times.")
        return 0

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, ST_Y(center_geog::geometry), ST_X(center_geog::geometry) FROM neighborhoods")
            neighborhoods = cur.fetchall()

            cur.execute("SELECT id, name, ST_Y(geog::geometry), ST_X(geog::geometry) FROM tech_parks")
            tech_parks = cur.fetchall()

            if not tech_parks:
                print("  No tech parks in DB. Run seed --transit first.")
                return 0

            cur.execute("DELETE FROM commute_times")
            count = 0

            tp_coords = [(tp[2], tp[3]) for tp in tech_parks]
            tp_ids = [tp[0] for tp in tech_parks]
            tp_names = [tp[1] for tp in tech_parks]

            # Next Monday 9 AM IST for peak traffic
            import datetime

            now = datetime.datetime.now(datetime.UTC)
            # Find next Monday
            days_ahead = 0 - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_monday = now + datetime.timedelta(days=days_ahead)
            peak_time = int(
                next_monday.replace(hour=3, minute=30, second=0, microsecond=0).timestamp()
            )  # 9 AM IST = 3:30 UTC
            offpeak_time = int(
                next_monday.replace(hour=8, minute=30, second=0, microsecond=0).timestamp()
            )  # 2 PM IST = 8:30 UTC

            total = len(neighborhoods)
            for batch_start in range(0, total, BATCH_SIZE):
                batch = neighborhoods[batch_start : batch_start + BATCH_SIZE]
                origins = [(n[2], n[3]) for n in batch]
                n_ids = [n[0] for n in batch]

                print(
                    f"  Batch {batch_start // BATCH_SIZE + 1}/{math.ceil(total / BATCH_SIZE)}: {len(batch)} neighborhoods x {len(tech_parks)} tech parks..."
                )

                # Peak traffic (9 AM Monday)
                try:
                    peak_result = _call_distance_matrix(origins, tp_coords, departure_time=peak_time)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"    Warning: Peak API call failed ({e}), skipping batch")
                    continue

                # Off-peak traffic (2 PM Monday)
                try:
                    offpeak_result = _call_distance_matrix(origins, tp_coords, departure_time=offpeak_time)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"    Warning: Off-peak API call failed ({e}), using peak data only")
                    offpeak_result = None

                for i, nid in enumerate(n_ids):
                    for j, tp_id in enumerate(tp_ids):
                        peak_row = peak_result["rows"][i]["elements"][j]
                        if peak_row["status"] != "OK":
                            continue

                        # duration = base route time (no traffic model)
                        # duration_in_traffic = real traffic-aware estimate
                        no_traffic_duration = peak_row["duration"]["value"] / 60.0
                        peak_duration = (
                            peak_row["duration_in_traffic"]["value"] / 60.0
                            if "duration_in_traffic" in peak_row
                            else no_traffic_duration
                        )
                        distance_km = peak_row["distance"]["value"] / 1000.0

                        offpeak_duration = no_traffic_duration
                        if offpeak_result:
                            offpeak_row = offpeak_result["rows"][i]["elements"][j]
                            if offpeak_row["status"] == "OK":
                                offpeak_duration = (
                                    offpeak_row["duration_in_traffic"]["value"] / 60.0
                                    if "duration_in_traffic" in offpeak_row
                                    else offpeak_row["duration"]["value"] / 60.0
                                )

                        # car_no_traffic: base route duration (Google's default, no traffic model)
                        cur.execute(
                            """INSERT INTO commute_times
                               (neighborhood_id, tech_park_id, mode, duration_min, distance_km, route_summary)
                               VALUES (%s, %s, 'car_no_traffic', %s, %s, %s)
                               ON CONFLICT (neighborhood_id, tech_park_id, mode) DO UPDATE SET
                                 duration_min = EXCLUDED.duration_min, distance_km = EXCLUDED.distance_km""",
                            (
                                nid,
                                tp_id,
                                round(no_traffic_duration, 1),
                                round(distance_km, 1),
                                f"Driving (no traffic) to {tp_names[j]}",
                            ),
                        )

                        # car_peak: Monday 9 AM with traffic
                        cur.execute(
                            """INSERT INTO commute_times
                               (neighborhood_id, tech_park_id, mode, duration_min, distance_km, route_summary)
                               VALUES (%s, %s, 'car_peak', %s, %s, %s)
                               ON CONFLICT (neighborhood_id, tech_park_id, mode) DO UPDATE SET
                                 duration_min = EXCLUDED.duration_min, distance_km = EXCLUDED.distance_km""",
                            (
                                nid,
                                tp_id,
                                round(peak_duration, 1),
                                round(distance_km, 1),
                                f"Driving (Mon 9AM traffic) to {tp_names[j]}",
                            ),
                        )

                        # car_offpeak: Monday 2 PM with traffic
                        cur.execute(
                            """INSERT INTO commute_times
                               (neighborhood_id, tech_park_id, mode, duration_min, distance_km, route_summary)
                               VALUES (%s, %s, 'car_offpeak', %s, %s, %s)
                               ON CONFLICT (neighborhood_id, tech_park_id, mode) DO UPDATE SET
                                 duration_min = EXCLUDED.duration_min, distance_km = EXCLUDED.distance_km""",
                            (
                                nid,
                                tp_id,
                                round(offpeak_duration, 1),
                                round(distance_km, 1),
                                f"Driving (Mon 2PM traffic) to {tp_names[j]}",
                            ),
                        )

                        # bike: estimated 1.3x no-traffic car time
                        bike_duration = no_traffic_duration * 1.3
                        cur.execute(
                            """INSERT INTO commute_times
                               (neighborhood_id, tech_park_id, mode, duration_min, distance_km, route_summary)
                               VALUES (%s, %s, 'bike', %s, %s, %s)
                               ON CONFLICT (neighborhood_id, tech_park_id, mode) DO UPDATE SET
                                 duration_min = EXCLUDED.duration_min, distance_km = EXCLUDED.distance_km""",
                            (
                                nid,
                                tp_id,
                                round(bike_duration, 1),
                                round(distance_km, 1),
                                f"Two-wheeler to {tp_names[j]}",
                            ),
                        )

                        count += 4

                conn.commit()

        print(f"  OK: {count} commute time records inserted ({count // 4} unique routes x 4 modes)")
    finally:
        conn.close()

    return count


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
