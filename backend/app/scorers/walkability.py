"""
Walkability Score (0-100)

METHODOLOGY: NEWS-India (Neighborhood Environment Walkability Scale — India)
Source: Sallis et al. 2016, MDPI Int. J. Environ. Res. Public Health 13(4):401
Reference: ICC 0.48-0.99 across subscales; 1-unit increase in aggregate
           score associated with 2x odds of travel-based physical activity.

Reads pre-computed scores from the walkability_zones DB table.
Scores are refreshed periodically via pipeline_walkability.py
which queries OpenStreetMap Overpass API in the background.
No external API calls at runtime.
"""

from app.db import get_pool
from app.models import NearbyDetail, ScoreResult, score_label

SOURCES = [
    "NEWS-India (Sallis et al. 2016, MDPI IJERPH 13(4):401)",
    "ITDP India StepUP walkability audit tool",
    "OpenStreetMap data (ODbL license) — pre-computed, refreshed periodically",
    "Bengaluru Walkability Datajam 2023 — opencity.in",
]


async def compute_walkability_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        zone = await conn.fetchrow(
            """SELECT area, score,
                      ST_Y(center_geog::geometry) as latitude,
                      ST_X(center_geog::geometry) as longitude,
                      ST_Distance(center_geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM walkability_zones
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon,
            lat,
        )

        parks_within_1km = 0
        nearest_park_km = None
        try:
            parks_within_1km = await conn.fetchval(
                "SELECT COUNT(*) FROM pois WHERE category = 'park' AND ST_DWithin(geog, ST_Point($1, $2)::geography, 1000)",
                lon,
                lat,
            )
            nearest_park = await conn.fetchrow(
                """SELECT name,
                          ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
                   FROM pois WHERE category = 'park'
                   ORDER BY geog <-> ST_Point($1, $2)::geography
                   LIMIT 1""",
                lon,
                lat,
            )
            if nearest_park:
                nearest_park_km = round(float(nearest_park["distance_km"]), 2)
        except Exception:
            pass

    if not zone:
        return ScoreResult(
            score=50.0, label="Average", data_confidence="low", sources=["No walkability data for this area"]
        )

    base_score = float(zone["score"])

    # Blend in green space bonus: up to 10 points if parks are nearby
    if parks_within_1km > 0:
        green_bonus = min(parks_within_1km * 2, 10)
        score = round(min(base_score * 0.9 + (base_score * 0.1 + green_bonus) * (green_bonus / 10), 100), 1)
    else:
        score = base_score

    details = [
        NearbyDetail(
            name=f"Walkability zone: {zone['area']} (pre-computed NEWS-India score)",
            distance_km=round(zone["distance_km"], 2),
            category="walkability_zone",
            latitude=zone["latitude"],
            longitude=zone["longitude"],
        )
    ]

    breakdown = {
        "methodology": "NEWS-India subscales (pre-computed from OSM data) + green space access",
        "matched_area": zone["area"],
        "distance_to_zone_center_km": round(zone["distance_km"], 2),
        "base_walkability_score": base_score,
        "parks_within_1km": parks_within_1km,
        "nearest_park_km": nearest_park_km,
    }

    return ScoreResult(
        score=score,
        label=score_label(score),
        details=details,
        breakdown=breakdown,
        sources=SOURCES,
    )
