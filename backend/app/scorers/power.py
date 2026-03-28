"""
Power Reliability Score (0-100)

METHODOLOGY: BESCOM outage data and tier classification
Source: bescom.karnataka.gov.in — scheduled outage notices
        NetZero India — Bangalore Power Cut tracker
        Deccan Herald (2023) — "Bengaluru's power cuts drop by 15%"
        Times of India — BESCOM underground cabling in 29 localities

BESCOM tiers:
  Tier 1: Underground cabling zones (central), ~2-4h outage/month
  Tier 2: Mixed infrastructure, ~6-8h outage/month
  Tier 3: Overhead lines (peripheral), ~10-12h outage/month
  Tier 4: Industrial/far peripheral, ~14-16h outage/month

Scores directly reflect BESCOM tier classification based on
published outage data — not a computed formula.
"""

from app.db import get_pool
from app.models import NearbyDetail, ScoreResult, score_label

SOURCES = [
    "BESCOM official outage notices (bescom.karnataka.gov.in)",
    "NetZero India — Bangalore Power Cut tracker",
    "BESCOM underground cabling data — Times of India (29 localities)",
    "Scoring reflects BESCOM tier classification directly (no arbitrary formula)",
]


async def compute_power_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        zone = await conn.fetchrow(
            """SELECT area, tier, avg_monthly_outage_hours, score,
                      ST_Y(center_geog::geometry) as latitude,
                      ST_X(center_geog::geometry) as longitude,
                      ST_Distance(center_geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM power_zones
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon,
            lat,
        )

    if not zone:
        return ScoreResult(score=50.0, label="Average", data_confidence="low", sources=["No BESCOM data"])

    final_score = float(zone["score"])
    tier_labels = {1: "Excellent (underground cabling)", 2: "Good", 3: "Moderate", 4: "Frequent outages"}

    details = [
        NearbyDetail(
            name=f"BESCOM Tier {zone['tier']} — {zone['area']} (~{zone['avg_monthly_outage_hours']}h outage/month)",
            distance_km=round(zone["distance_km"], 2),
            category=f"power_tier_{zone['tier']}",
            latitude=zone["latitude"],
            longitude=zone["longitude"],
        )
    ]

    return ScoreResult(
        score=final_score,
        label=score_label(final_score),
        details=details,
        breakdown={
            "methodology": "BESCOM tier classification (direct, not computed)",
            "bescom_tier": zone["tier"],
            "tier_label": tier_labels.get(zone["tier"], "Unknown"),
            "avg_monthly_outage_hours": zone["avg_monthly_outage_hours"],
            "area": zone["area"],
        },
        sources=SOURCES,
    )
