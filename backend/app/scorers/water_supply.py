"""
Water Supply Score (0-100)

METHODOLOGY: BWSSB Stage-wise Cauvery Water Supply Classification
Source: data.opencity.in — BWSSB Stage-wise Cauvery Water Supply Areas (CC BY 4.0)
        bwssb.karnataka.gov.in — Bangalore Water Supply and Sewerage Board
        The Hindu (2025) — "In a year since Cauvery Stage V was commissioned..."

BWSSB stages:
  Stage 1-2: Old Bangalore core, 4-6h/day, high reliability
  Stage 3: Mid-ring expansion, 3h/day, medium reliability
  Stage 4: Peripheral areas, 2h/day, low reliability (borewell/tanker dependent)
  Stage 5: Planned/partially operational, very low reliability

Scores are directly from BWSSB zone classification — not a computed formula.
The stage system itself is the authoritative assessment of water access in Bangalore.
"""

from app.db import get_pool
from app.models import ScoreResult, NearbyDetail, score_label

SOURCES = [
    "BWSSB Stage-wise Cauvery Water Supply Areas — data.opencity.in (CC BY 4.0)",
    "Bangalore Water Supply and Sewerage Board (bwssb.karnataka.gov.in)",
    "Bengaluru Water Tankers Survey 2025 — opencity.in",
    "Scoring reflects BWSSB stage classification directly (no arbitrary formula)",
]


async def compute_water_supply_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        zone = await conn.fetchrow(
            """SELECT area, stage, supply_hours, reliability, score,
                      ST_Y(center_geog::geometry) as latitude,
                      ST_X(center_geog::geometry) as longitude,
                      ST_Distance(center_geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM water_zones
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

    if not zone:
        return ScoreResult(score=30.0, label="Below Average", data_confidence="low", sources=["No BWSSB data"])

    final_score = float(zone["score"])
    stage_label = f"Stage {zone['stage']}"
    if zone["stage"] == 5:
        stage_label = "Stage 5 (planned, not fully operational)"

    details = [
        NearbyDetail(
            name=f"BWSSB {stage_label} — {zone['area']} ({zone['supply_hours']}h/day, {zone['reliability']} reliability)",
            distance_km=round(zone["distance_km"], 2),
            category=f"water_stage_{zone['stage']}",
            latitude=zone["latitude"], longitude=zone["longitude"],
        )
    ]

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details,
        breakdown={
            "methodology": "BWSSB stage classification (direct, not computed)",
            "cauvery_stage": zone["stage"],
            "supply_hours_per_day": zone["supply_hours"],
            "reliability": zone["reliability"],
            "area": zone["area"],
        },
        sources=SOURCES,
    )
