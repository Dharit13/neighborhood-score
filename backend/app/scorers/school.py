"""
School Access Score (0-100)

METHODOLOGY: Right to Education Act 2009, Section 6
Source: education.gov.in — RTE Act Section 6
        PIB Press Release PRID/1578389

RTE norms:
  - Primary school: within 1 km of every habitation
  - Upper primary school: within 3 km
  - 97.15% national habitation coverage at these norms

Scoring:
  1. RTE compliance (30%): school exists within RTE norms (1km/3km)
  2. Quality proximity (25%): proximity to top-25 ranked schools
  3. Board diversity (15%): variety of boards (CBSE/ICSE/IB) within 5km
  4. Admission accessibility (15%): weighted by admission difficulty of nearby schools
  5. Fee affordability (15%): fee range distribution of nearby schools

Data: Unified pois table (Google Places bulk + curated ranked schools).
"""

import json
from app.db import get_pool
from app.utils.geo import decay_score
from app.models import ScoreResult, NearbyDetail, score_label

RTE_PRIMARY_RADIUS_KM = 1.0
RTE_UPPER_PRIMARY_RADIUS_KM = 3.0

ADMISSION_DIFFICULTY_SCORES = {
    "easy": 100,
    "moderate": 75,
    "competitive": 45,
    "very_competitive": 20,
}

SOURCES = [
    "RTE Act 2009, Section 6 — 1km primary, 3km upper primary norms",
    "Times Now Education / IIRF School Rankings 2024",
    "97.15% national habitation coverage at RTE norms (PIB 2019)",
    "SchoolMyKids.com fee data 2024-25",
    "Google Places API — bulk pipeline data",
]


def _parse_fee_low(fee_str: str | None) -> float | None:
    if not fee_str:
        return None
    try:
        return float(fee_str.split("-")[0])
    except (ValueError, IndexError):
        return None


async def compute_school_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        within_primary = await conn.fetchval(
            "SELECT COUNT(*) FROM pois WHERE category = 'school' AND ST_DWithin(geog, ST_Point($1, $2)::geography, $3)",
            lon, lat, RTE_PRIMARY_RADIUS_KM * 1000,
        )

        within_upper = await conn.fetchval(
            "SELECT COUNT(*) FROM pois WHERE category = 'school' AND ST_DWithin(geog, ST_Point($1, $2)::geography, $3)",
            lon, lat, RTE_UPPER_PRIMARY_RADIUS_KM * 1000,
        )

        nearest_ranked = await conn.fetch(
            """SELECT name, tags,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM pois
               WHERE category = 'school' AND (tags->>'rank') IS NOT NULL
                 AND (tags->>'rank')::int <= 25
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 5""",
            lon, lat,
        )

        nearest_other_ranked = await conn.fetch(
            """SELECT name, tags,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM pois
               WHERE category = 'school' AND (tags->>'rank') IS NOT NULL
                 AND (tags->>'rank')::int > 25
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 5""",
            lon, lat,
        )

        boards_nearby = await conn.fetch(
            """SELECT DISTINCT split_part(tags->>'board', '/', 1) as b
               FROM pois
               WHERE category = 'school'
                 AND (tags->>'board') IS NOT NULL
                 AND ST_DWithin(geog, ST_Point($1, $2)::geography, 5000)""",
            lon, lat,
        )

        nearby_with_tags = await conn.fetch(
            """SELECT tags
               FROM pois
               WHERE category = 'school'
                 AND (tags->>'admission_difficulty') IS NOT NULL
                 AND ST_DWithin(geog, ST_Point($1, $2)::geography, 5000)""",
            lon, lat,
        )

        total_nearby = await conn.fetchval(
            "SELECT COUNT(*) FROM pois WHERE category = 'school' AND ST_DWithin(geog, ST_Point($1, $2)::geography, 5000)",
            lon, lat,
        )

    # --- Component 1: RTE compliance (30%) ---
    if within_primary > 0:
        rte_score = 100.0
    elif within_upper > 0:
        rte_score = 60.0
    else:
        rte_score = 20.0

    # --- Component 2: Quality proximity (25%) ---
    if nearest_ranked:
        top_prox = decay_score(float(nearest_ranked[0]["distance_km"]), RTE_PRIMARY_RADIUS_KM, 5.0)
        top_within_3 = sum(1 for s in nearest_ranked if s["distance_km"] <= RTE_UPPER_PRIMARY_RADIUS_KM)
        bonus = min(top_within_3 * 0.1, 0.3)
        quality_score = min((top_prox + bonus), 1.0) * 100
    else:
        quality_score = 0.0

    # --- Component 3: Board diversity (15%) ---
    board_set = {r["b"] for r in boards_nearby if r["b"]}
    diversity_score = min(len(board_set) / 4.0, 1.0) * 100

    # --- Component 4: Admission accessibility (15%) ---
    admission_entries = []
    fee_entries = []
    for r in nearby_with_tags:
        tags = json.loads(r["tags"]) if isinstance(r["tags"], str) else r["tags"]
        ad = tags.get("admission_difficulty")
        if ad:
            admission_entries.append(ad)
        fr = tags.get("fee_range")
        if fr:
            fee_entries.append(fr)

    if admission_entries:
        diff_scores = [ADMISSION_DIFFICULTY_SCORES.get(d, 50) for d in admission_entries]
        admission_score = sum(diff_scores) / len(diff_scores)
    else:
        admission_score = 50.0

    # --- Component 5: Fee affordability (15%) ---
    fee_lows = [_parse_fee_low(f) for f in fee_entries]
    fee_lows = [f for f in fee_lows if f is not None]
    if fee_lows:
        avg_fee = sum(fee_lows) / len(fee_lows)
        fee_score = max(0, min(100, (10.0 - avg_fee) / 9.5 * 100))
    else:
        fee_score = 50.0

    final_score = round(min(max(
        0.30 * rte_score + 0.25 * quality_score + 0.15 * diversity_score
        + 0.15 * admission_score + 0.15 * fee_score,
        0), 100), 1)

    DIFFICULTY_LABELS = {
        "easy": "Easy",
        "moderate": "Moderate",
        "competitive": "Competitive",
        "very_competitive": "Very Competitive",
    }

    details = []
    seen_ranks: set[int] = set()

    all_ranked = list(nearest_ranked) + list(nearest_other_ranked)
    all_ranked.sort(key=lambda x: x["distance_km"])

    for s in all_ranked[:30]:
        tags = json.loads(s["tags"]) if isinstance(s["tags"], str) else s["tags"]
        rank = tags.get("rank")
        if rank in seen_ranks:
            continue
        seen_ranks.add(rank)
        parts = [f"Rank #{tags.get('rank', '?')}", tags.get("board", "")]
        if tags.get("fee_range"):
            parts.append(f"Fee: {tags['fee_range']}L/yr")
        if tags.get("admission_difficulty"):
            parts.append(DIFFICULTY_LABELS.get(tags["admission_difficulty"], tags["admission_difficulty"]))
        details.append(NearbyDetail(
            name=f"{s['name']} ({', '.join(p for p in parts if p)})",
            distance_km=round(s["distance_km"], 2),
            category="school_rank",
            latitude=s["latitude"], longitude=s["longitude"],
        ))

    admission_summary = {}
    for d in admission_entries:
        admission_summary[d] = admission_summary.get(d, 0) + 1

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details[:15],
        breakdown={
            "methodology": "RTE Act 2009 Section 6 + admission difficulty + fee affordability",
            "rte_compliance": round(rte_score, 1),
            "quality_proximity": round(quality_score, 1),
            "board_diversity": round(diversity_score, 1),
            "admission_accessibility": round(admission_score, 1),
            "fee_affordability": round(fee_score, 1),
            "schools_within_1km": within_primary,
            "schools_within_3km": within_upper,
            "total_schools_nearby": total_nearby,
            "boards_available": sorted(board_set),
            "nearby_admission_difficulty": admission_summary,
            "avg_min_fee_lakh": round(sum(fee_lows) / len(fee_lows), 1) if fee_lows else None,
        },
        sources=SOURCES,
    )
