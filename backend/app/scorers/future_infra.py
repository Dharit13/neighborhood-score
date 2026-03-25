"""
Future Infrastructure Score (0-100)

METHODOLOGY: MOHUA TOD Policy (2017) proximity norms + completion timeline weighting
Source: mohua.gov.in TOD Policy — 500m optimal, 800m acceptable catchment
        booknewproperty.com Metro Phase 2A/2B Tracker (Jan 2026)
        Wikipedia — Bengaluru Suburban Railway
        Times of India — Bengaluru Business Corridor (Rs 27,000 cr)

Proximity uses same MOHUA TOD 500m/800m norms as transit scorer.
Completion weighting: projects completing sooner get more weight
(factual: construction years, not arbitrary).
"""

from app.db import get_pool
from app.models import ScoreResult, NearbyDetail, score_label

# MOHUA TOD distance norms (meters)
TOD_OPTIMAL_M = 500
TOD_ACCEPTABLE_M = 800

SOURCES = [
    "MOHUA TOD Policy (2017) — 500m/800m proximity norms",
    "Namma Metro Phase 2A/2B — booknewproperty.com Tracker",
    "Bengaluru Suburban Railway — Wikipedia / K-RIDE",
    "Bengaluru Business Corridor — Times of India",
]


def _completion_weight(expected: str | None) -> float:
    """Closer completion = higher weight. Purely timeline-based."""
    if not expected:
        return 0.3
    try:
        year = int(expected.split("-")[0])
    except (ValueError, IndexError):
        return 0.3
    if year <= 2026:
        return 1.0
    elif year <= 2027:
        return 0.85
    elif year <= 2028:
        return 0.7
    elif year <= 2029:
        return 0.55
    return 0.4


def _tod_decay(distance_m: float) -> float:
    """MOHUA TOD decay: 100% at 500m, 50% at 800m, 0% at 3000m."""
    if distance_m <= TOD_OPTIMAL_M:
        return 1.0
    if distance_m <= TOD_ACCEPTABLE_M:
        return 1.0 - 0.5 * (distance_m - TOD_OPTIMAL_M) / (TOD_ACCEPTABLE_M - TOD_OPTIMAL_M)
    if distance_m <= 3000:
        return 0.5 - 0.5 * (distance_m - TOD_ACCEPTABLE_M) / (3000 - TOD_ACCEPTABLE_M)
    return 0.0


async def compute_future_infra_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        nearby = await conn.fetch(
            """SELECT s.name as station_name,
                      ST_Y(s.geog::geometry) as latitude, ST_X(s.geog::geometry) as longitude,
                      ST_Distance(s.geog, ST_Point($1, $2)::geography) as distance_m,
                      ST_Distance(s.geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km,
                      p.name as project_name, p.type, p.status, p.expected_completion
               FROM future_infra_stations s
               JOIN future_infra_projects p ON s.project_id = p.id
               WHERE ST_DWithin(s.geog, ST_Point($1, $2)::geography, 5000)
               ORDER BY ST_Distance(s.geog, ST_Point($1, $2)::geography)""",
            lon, lat,
        )

    if not nearby:
        return ScoreResult(
            score=20.0, label="Below Average", data_confidence="low",
            breakdown={"projects_within_5km": 0},
            sources=["No planned infrastructure projects within 5km"],
        )

    within_tod = [s for s in nearby if s["distance_m"] <= TOD_ACCEPTABLE_M]
    within_2km = [s for s in nearby if s["distance_m"] <= 2000]
    within_3km = [s for s in nearby if s["distance_m"] <= 3000]

    # TOD-based proximity score
    proximity_score = 0.0
    for s in within_2km[:5]:
        contribution = _tod_decay(float(s["distance_m"]))
        proximity_score += contribution * _completion_weight(s["expected_completion"]) * 20
    proximity_score = min(proximity_score, 60)

    # Diversity bonus: multiple project types
    project_names = set(s["project_name"] for s in within_3km)
    diversity_bonus = min(len(project_names) * 8, 25)

    # Construction bonus: active work nearby
    construction_bonus = 15 if any(s["status"] == "under_construction" for s in within_2km) else 0

    final_score = round(min(proximity_score + diversity_bonus + construction_bonus, 100), 1)

    details = []
    seen = set()
    for s in nearby[:10]:
        if s["station_name"] not in seen:
            seen.add(s["station_name"])
            details.append(NearbyDetail(
                name=f"{s['station_name']} ({s['project_name']}) — {s['status'].replace('_', ' ').title()}, ETA {(s['expected_completion'] or '')[:4]}",
                distance_km=round(s["distance_km"], 2),
                category=f"future_{s['type']}",
                latitude=s["latitude"], longitude=s["longitude"],
            ))

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details[:8],
        breakdown={
            "methodology": "MOHUA TOD 500m/800m norms + completion timeline",
            "proximity_score": round(proximity_score, 1),
            "diversity_bonus": diversity_bonus,
            "construction_bonus": construction_bonus,
            "stations_within_tod_800m": len(within_tod),
            "stations_within_2km": len(within_2km),
            "stations_within_5km": len(nearby),
            "projects_nearby": sorted(project_names),
        },
        sources=SOURCES,
    )
