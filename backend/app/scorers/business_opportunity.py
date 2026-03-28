"""
Business Opportunity Score (0-100)

METHODOLOGY: Karnataka Startup Cell + BBMP Trade License + NASSCOM
Source: Karnataka Startup Cell (startup.karnataka.gov.in)
        BBMP Trade License Data 2024-25
        NASSCOM Startup Report 2025
        RBI/CIBIL MSME Data Karnataka

Data is already seeded in business_opportunity table via seed_prices.py.
This scorer reads the pre-computed score and surfaces the breakdown.
"""

from app.db import get_pool
from app.models import ScoreResult, score_label

SOURCES = [
    "Karnataka Startup Cell — startup.karnataka.gov.in",
    "BBMP Trade License Data 2024-25 — data.opencity.in",
    "NASSCOM Startup Ecosystem Report 2025",
    "RBI/CIBIL MSME Data Karnataka",
    "JustDial / Google Maps commercial listings",
    "WeWork / 91springboard / Awfis coworking locations",
]


async def compute_business_opportunity_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT bo.area, bo.new_business_acceptability_pct,
                      bo.commercial_rent_sqft, bo.footfall_index,
                      bo.startup_density, bo.coworking_spaces,
                      bo.consumer_spending_index, bo.business_type_fit,
                      bo.score, bo.label,
                      ST_Distance(n.center_geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM business_opportunity bo
               JOIN neighborhoods n ON bo.neighborhood_id = n.id
               ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon,
            lat,
        )

    if not row:
        return ScoreResult(
            score=40.0,
            label="Below Average",
            data_confidence="low",
            breakdown={"note": "No business opportunity data"},
            sources=["No data available"],
        )

    score = float(row["score"])
    business_types = row["business_type_fit"] or []

    return ScoreResult(
        score=score,
        label=score_label(score),
        breakdown={
            "methodology": "Karnataka Startup Cell + BBMP Trade License + NASSCOM",
            "area": row["area"],
            "new_business_acceptability_pct": row["new_business_acceptability_pct"],
            "commercial_rent_sqft": row["commercial_rent_sqft"],
            "footfall_index": row["footfall_index"],
            "startup_density_per_sqkm": row["startup_density"],
            "coworking_spaces": row["coworking_spaces"],
            "consumer_spending_index": row["consumer_spending_index"],
            "best_business_types": business_types,
        },
        sources=SOURCES,
    )
