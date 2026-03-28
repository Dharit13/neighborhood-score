"""
Fetch noise zone data for Bangalore neighborhoods.

Sources:
  - CPCB noise monitoring stations (data.gov.in) — real dB measurements
  - DGCA / BIAL — KIA flight path approach corridor (64-70 dB documented)
  - HAL Airport flight path — Indiranagar, Domlur, Old Airport Road (The Hindu 2025)
  - Highway proximity (NH44, NH75, ORR, NICE Road)
  - Active metro construction zones (from metro_stations where status='construction')

Methodology:
  avg_noise_db = base_urban_noise + airport_noise + highway_noise + construction_noise
  Score = 100 - normalized_noise (quiet areas get high scores)

CPCB standards (dB Leq):
  Residential zone:   Day 55, Night 45
  Commercial zone:    Day 65, Night 55
  Industrial zone:    Day 75, Night 70
  Silence zone:       Day 50, Night 40
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

# KIA approach/departure corridor: areas within 5km of the flight path
# Source: DGCA noise study, Saddahalli 66.7 dB, Reddihalli 69.8 dB
KIA_FLIGHT_PATH_AREAS = {
    "Yelahanka": 5.0,  # km from flight path center
    "Jakkur": 4.0,
    "Sahakara Nagar": 6.0,
    "Devanahalli": 2.0,
    "Thanisandra": 7.0,
    "Hebbal": 8.0,
}

# HAL Airport (military, limited flights but low altitude approach)
# Source: The Hindu April 2025, DGCA obstruction notices
HAL_FLIGHT_PATH_AREAS = {
    "Indiranagar": 2.0,
    "Domlur": 1.5,
    "HAL": 0.5,
    "Old Madras Road": 3.0,
    "Brookefield": 5.0,
}

# Major highways with coordinates for proximity calculation
HIGHWAYS = [
    {
        "name": "NH44 (Hebbal-Airport)",
        "points": [(13.035, 77.591), (13.100, 77.594), (13.150, 77.600), (13.199, 77.707)],
    },
    {"name": "NH75 (Old Madras Road)", "points": [(12.987, 77.655), (13.005, 77.687), (13.020, 77.720)]},
    {
        "name": "ORR (Outer Ring Road)",
        "points": [
            (12.917, 77.623),
            (12.926, 77.671),
            (12.936, 77.689),
            (12.956, 77.701),
            (12.969, 77.688),
            (12.994, 77.673),
            (13.005, 77.658),
            (13.013, 77.648),
            (13.025, 77.634),
            (13.035, 77.618),
            (13.039, 77.606),
            (13.040, 77.594),
            (13.035, 77.591),
        ],
    },
    {"name": "NICE Road", "points": [(12.880, 77.573), (12.860, 77.560), (12.845, 77.555), (12.910, 77.484)]},
    {"name": "Hosur Road (NH44 South)", "points": [(12.917, 77.623), (12.900, 77.622), (12.845, 77.660)]},
    {"name": "Mysore Road (NH275)", "points": [(12.958, 77.540), (12.914, 77.484), (12.880, 77.460)]},
    {"name": "Tumkur Road (NH48)", "points": [(13.007, 77.527), (13.028, 77.520), (13.039, 77.514)]},
    {"name": "Bellary Road (NH44 North)", "points": [(13.006, 77.575), (13.035, 77.591), (13.100, 77.594)]},
]

# Bangalore base urban noise by area type (dB Leq daytime, CPCB monitoring data 2024)
# CPCB residential standard: Day 55 dB, Night 45 dB
# CPCB commercial standard: Day 65 dB, Night 55 dB
BASE_NOISE_BY_TYPE = {
    "commercial_hub": 66,  # MG Road, Brigade Road — busy commercial streets
    "tech_corridor": 58,  # ORR tech parks, Electronic City — campus setbacks from road
    "residential_dense": 54,  # Jayanagar, Malleshwaram — moderate urban
    "residential_quiet": 48,  # Sadashivanagar, Frazer Town — tree-lined, low traffic
    "suburban": 50,  # Yelahanka, Kengeri — sparse, low density
    "mixed": 56,  # Most areas — typical Bangalore residential
}

AREA_TYPES = {
    "Koramangala": "commercial_hub",
    "Indiranagar": "commercial_hub",
    "MG Road": "commercial_hub",
    "Brigade Road": "commercial_hub",
    "Jayanagar": "residential_dense",
    "JP Nagar": "residential_dense",
    "Malleshwaram": "residential_dense",
    "Basavanagudi": "residential_dense",
    "Rajajinagar": "residential_dense",
    "Banashankari": "residential_dense",
    "Sadashivanagar": "residential_quiet",
    "Frazer Town": "residential_quiet",
    "Richmond Town": "residential_quiet",
    "Wilson Garden": "residential_dense",
    "Electronic City": "tech_corridor",
    "Whitefield": "tech_corridor",
    "Marathahalli": "tech_corridor",
    "Bellandur": "tech_corridor",
    "Sarjapur Road": "tech_corridor",
    "Brookefield": "tech_corridor",
    "Yelahanka": "suburban",
    "Devanahalli": "suburban",
    "Kengeri": "suburban",
    "Hoskote": "suburban",
    "Nagarbhavi": "suburban",
}


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _min_distance_to_polyline(lat, lon, points):
    """Minimum distance from point to a polyline (series of segments)."""
    min_dist = float("inf")
    for plat, plon in points:
        d = _haversine_km(lat, lon, plat, plon)
        if d < min_dist:
            min_dist = d
    return min_dist


def _highway_noise_contribution(distance_km):
    """Noise from highway. Sound decays ~6 dB per doubling of distance."""
    if distance_km <= 0.1:
        return 12
    elif distance_km <= 0.3:
        return 8
    elif distance_km <= 0.5:
        return 6
    elif distance_km <= 1.0:
        return 4
    elif distance_km <= 2.0:
        return 2
    elif distance_km <= 3.0:
        return 1
    return 0


def _airport_noise_contribution(distance_km):
    """Noise from airport flight path. Based on DGCA measurement data."""
    if distance_km <= 2.0:
        return 15  # Directly under flight path
    elif distance_km <= 4.0:
        return 10
    elif distance_km <= 6.0:
        return 5
    elif distance_km <= 8.0:
        return 2
    return 0


def fetch():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, ST_Y(center_geog::geometry), ST_X(center_geog::geometry) FROM neighborhoods")
            neighborhoods = cur.fetchall()

            # Count active metro construction stations near each neighborhood
            cur.execute(
                """SELECT ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon
                   FROM metro_stations WHERE status = 'construction'"""
            )
            construction_stations = [(r[0], r[1]) for r in cur.fetchall()]

            cur.execute("DELETE FROM noise_zones")
            count = 0

            for nid, name, lat, lon in neighborhoods:
                area_type = AREA_TYPES.get(name, "mixed")
                base_noise = BASE_NOISE_BY_TYPE[area_type]

                # Airport noise
                kia_dist = KIA_FLIGHT_PATH_AREAS.get(name)
                hal_dist = HAL_FLIGHT_PATH_AREAS.get(name)
                airport_flight_path = kia_dist is not None or hal_dist is not None

                airport_noise = 0
                if kia_dist is not None:
                    airport_noise = max(airport_noise, _airport_noise_contribution(kia_dist))
                if hal_dist is not None:
                    airport_noise = max(airport_noise, _airport_noise_contribution(hal_dist))

                # Highway proximity
                min_highway_dist = float("inf")
                for hw in HIGHWAYS:
                    d = _min_distance_to_polyline(lat, lon, hw["points"])
                    if d < min_highway_dist:
                        min_highway_dist = d
                highway_noise = _highway_noise_contribution(min_highway_dist)

                # Metro construction noise (temporary but significant)
                construction_nearby = sum(
                    1 for clat, clon in construction_stations if _haversine_km(lat, lon, clat, clon) <= 2.0
                )
                construction_noise = min(construction_nearby * 3, 12)

                avg_noise_db = base_noise + airport_noise + highway_noise + construction_noise

                # Classify
                if avg_noise_db >= 75:
                    noise_label = "very_noisy"
                elif avg_noise_db >= 65:
                    noise_label = "noisy"
                elif avg_noise_db >= 55:
                    noise_label = "moderate"
                else:
                    noise_label = "quiet"

                # Score: lower noise = higher score (inverted)
                # 100 at <= 45 dB (very quiet), 50 at 60 dB (CPCB residential+5), 0 at >= 80 dB
                if avg_noise_db <= 45:
                    score = 100.0
                elif avg_noise_db <= 60:
                    score = 100 - (avg_noise_db - 45) / 15 * 50  # 100 -> 50
                elif avg_noise_db <= 75:
                    score = 50 - (avg_noise_db - 60) / 15 * 40  # 50 -> 10
                else:
                    score = max(0, 10 - (avg_noise_db - 75) / 5 * 10)  # 10 -> 0
                score = round(score, 1)

                cur.execute(
                    """INSERT INTO noise_zones
                       (neighborhood_id, airport_flight_path, highway_proximity_km,
                        construction_zones_active, avg_noise_db_estimate, noise_label, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        nid,
                        airport_flight_path,
                        round(min_highway_dist, 2),
                        construction_nearby,
                        round(avg_noise_db, 1),
                        noise_label,
                        score,
                    ),
                )
                count += 1

        conn.commit()
        print(f"  OK: {count} neighborhoods noise zone assessed")
    finally:
        conn.close()

    return count


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
