"""
Builder Reputation Score (0-100)

METHODOLOGY: RERA Karnataka Quarterly Compliance Framework
Source: rera.karnataka.gov.in — Real Estate Regulatory Authority Karnataka
        RERA compliance: 70% escrow, quarterly certificates (Forms 1-3)
        BrickFi Builder Reputation Guide 2025

RERA Karnataka tracks:
  - Registered projects and quarterly compliance submissions
  - Complaints filed and resolution rate
  - 70% escrow account adherence
  - Delivery timeline compliance

Builder score = weighted average of active-area builders' RERA metrics.
"""

from app.db import get_pool
from app.models import BuilderDetail, BuilderScoreResult, score_label

SOURCES = [
    "RERA Karnataka Portal (rera.karnataka.gov.in)",
    "RERA quarterly compliance: Forms 1-3, 70% escrow, delivery tracking",
    "BrickFi Builder Reputation Guide 2025",
    "MagicBricks / 99acres builder reviews",
]


async def compute_builder_score(
    lat: float, lon: float, address: str = "", builder_name: str | None = None
) -> BuilderScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT name, rera_projects, total_projects_blr, complaints,
                      complaints_ratio, on_time_delivery_pct, avg_rating,
                      reputation_tier, active_areas, score
               FROM builders ORDER BY score DESC"""
        )

    area_keywords = _extract_area_from_address(address)

    builder_details = []
    for b in rows:
        active_in_area = (
            any(_area_match(b["active_areas"] or [], kw) for kw in area_keywords) if area_keywords else False
        )

        pct = b["on_time_delivery_pct"] or 0
        delivery_rating = (
            "Excellent" if pct >= 85 else "Good" if pct >= 75 else "Average" if pct >= 65 else "Below Average"
        )

        builder_details.append(
            BuilderDetail(
                name=b["name"],
                score=b["score"],
                rera_projects=b["rera_projects"],
                complaints=b["complaints"],
                complaints_ratio=b["complaints_ratio"],
                delivery_rating=delivery_rating,
                active_in_area=active_in_area,
            )
        )

    if builder_name:
        name_lower = builder_name.lower()
        matching = [bd for bd in builder_details if name_lower in bd.name.lower()]
        if matching:
            builder_details = matching + [bd for bd in builder_details if bd not in matching]

    active_builders = [bd for bd in builder_details if bd.active_in_area]
    if active_builders:
        area_avg_score = sum(bd.score for bd in active_builders) / len(active_builders)
    else:
        top_builders = sorted(builder_details, key=lambda x: x.score, reverse=True)[:10]
        area_avg_score = sum(bd.score for bd in top_builders) / len(top_builders)

    final_score = round(area_avg_score, 1)
    builder_details.sort(key=lambda x: (-x.active_in_area, -x.score))

    # Split into recommended and avoid lists
    recommended = [bd for bd in builder_details if bd.active_in_area and bd.score >= 70 and bd.complaints_ratio < 1.5]
    to_avoid = []
    for bd in builder_details:
        if not bd.active_in_area:
            continue
        reasons = []
        if bd.score < 55:
            reasons.append(f"Low RERA score ({bd.score})")
        if bd.complaints_ratio > 2.0:
            reasons.append(f"High complaint ratio ({bd.complaints_ratio})")
        if bd.delivery_rating == "Below Average":
            reasons.append("Below average on-time delivery")
        if reasons:
            bd.avoid_reason = "; ".join(reasons)
            to_avoid.append(bd)

    return BuilderScoreResult(
        score=final_score,
        label=score_label(final_score),
        details=[],
        breakdown={
            "methodology": "RERA Karnataka quarterly compliance metrics",
            "area_average_score": final_score,
            "active_builders_in_area": len(active_builders),
            "recommended_count": len(recommended),
            "avoid_count": len(to_avoid),
            "total_builders_tracked": len(builder_details),
            "area_keywords": area_keywords,
        },
        builders=builder_details[:15],
        recommended_builders=recommended[:5],
        builders_to_avoid=to_avoid[:5],
        sources=SOURCES,
    )


def _area_match(builder_areas: list[str], query_area: str) -> bool:
    query_lower = query_area.lower()
    return any(a.lower() in query_lower or query_lower in a.lower() for a in builder_areas)


def _extract_area_from_address(address: str) -> list[str]:
    known_areas = [
        "Whitefield",
        "Sarjapur",
        "Hennur",
        "Yelahanka",
        "Electronic City",
        "Bannerghatta",
        "Kanakapura",
        "Hebbal",
        "Indiranagar",
        "Koramangala",
        "JP Nagar",
        "Jayanagar",
        "Marathahalli",
        "Brookefield",
        "Old Madras Road",
        "Rajajinagar",
        "Malleshwaram",
        "HSR Layout",
        "BTM Layout",
        "Devanahalli",
        "KR Puram",
        "Thanisandra",
        "Sahakara Nagar",
        "Basavanagudi",
        "Banashankari",
        "Vijayanagar",
        "Kengeri",
        "Bommanahalli",
        "Hosur Road",
    ]
    address_lower = address.lower()
    return [a for a in known_areas if a.lower() in address_lower]
