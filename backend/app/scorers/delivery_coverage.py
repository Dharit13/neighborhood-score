"""
Delivery Coverage Score (0-100)

METHODOLOGY: Quick-commerce service availability verification
Source: Zepto delivery areas (zepto.com/delivery-areas, Mar 2026)
        Blinkit dark store expansion (mystoreslist.com, Aug 2025)
        Swiggy Instamart 10-minute delivery coverage (100+ cities, Mar 2026)
        BigBasket coverage (widest in Bangalore, since 2011)

Score = (services_available / 4) * 80 + delivery_time_bonus
Services checked: Swiggy Instamart, Zepto, Blinkit, BigBasket
"""

from app.db import get_pool
from app.models import ScoreResult, score_label

SOURCES = [
    "Zepto Delivery Areas — zepto.com/delivery-areas (Mar 2026)",
    "Blinkit Dark Store Expansion — mystoreslist.com (Aug 2025)",
    "Swiggy Instamart — 10-minute delivery coverage (Mar 2026)",
    "BigBasket — Bangalore coverage map (Mar 2026)",
]


async def compute_delivery_coverage_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT dc.swiggy_serviceable, dc.zepto_serviceable,
                      dc.blinkit_serviceable, dc.bigbasket_serviceable,
                      dc.avg_delivery_min, dc.coverage_score,
                      n.name as neighborhood
               FROM delivery_coverage dc
               JOIN neighborhoods n ON dc.neighborhood_id = n.id
               ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

    if not row:
        return ScoreResult(
            score=40.0, label="Below Average", data_confidence="low",
            breakdown={"note": "No delivery coverage data"},
            sources=["No delivery data available"],
        )

    score = float(row["coverage_score"])
    services = {
        "Swiggy Instamart": row["swiggy_serviceable"],
        "Zepto": row["zepto_serviceable"],
        "Blinkit": row["blinkit_serviceable"],
        "BigBasket": row["bigbasket_serviceable"],
    }
    available = [name for name, avail in services.items() if avail]
    unavailable = [name for name, avail in services.items() if not avail]

    return ScoreResult(
        score=score,
        label=score_label(score),
        breakdown={
            "methodology": "Quick-commerce service availability check",
            "neighborhood": row["neighborhood"],
            "services_available": available,
            "services_unavailable": unavailable,
            "coverage_count": len(available),
            "avg_delivery_min": row["avg_delivery_min"],
        },
        sources=SOURCES,
    )
