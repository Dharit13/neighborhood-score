"""
Commute Score (0-100)

METHODOLOGY: Google Maps Distance Matrix API — real traffic-aware commute times
Source: Google Maps Distance Matrix API (driving mode, departure_time-aware)
        Tech park locations from seed data (Manyata, Embassy, ITPL, Electronic City, etc.)

Scoring bands (weighted average of commute to top 3 nearest tech parks):
  <20 min:   100 (excellent commute)
  20-30 min:  85
  30-45 min:  65
  45-60 min:  45
  60-90 min:  25
  >90 min:     5 (very poor commute)
"""

from app.db import get_pool
from app.models import ScoreResult, NearbyDetail, score_label

SOURCES = [
    "Google Maps Distance Matrix API — real traffic-aware driving times",
    "Tech park locations: Manyata, Embassy TechVillage, ITPL, Electronic City, etc.",
    "Peak traffic: Monday 9 AM IST departure",
    "Off-peak traffic: Monday 2 PM IST departure",
]


def _commute_score(duration_min: float) -> float:
    """Convert peak commute duration to score."""
    if duration_min <= 20:
        return 100.0
    elif duration_min <= 30:
        return 100 - (duration_min - 20) / 10 * 15  # 100 -> 85
    elif duration_min <= 45:
        return 85 - (duration_min - 30) / 15 * 20  # 85 -> 65
    elif duration_min <= 60:
        return 65 - (duration_min - 45) / 15 * 20  # 65 -> 45
    elif duration_min <= 90:
        return 45 - (duration_min - 60) / 30 * 20  # 45 -> 25
    else:
        return max(5, 25 - (duration_min - 90) / 30 * 20)  # 25 -> 5


async def compute_commute_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Find nearest neighborhood
        neighborhood = await conn.fetchrow(
            """SELECT id, name FROM neighborhoods
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

        if not neighborhood:
            return ScoreResult(
                score=50.0, label="Average", data_confidence="low",
                breakdown={"note": "No neighborhood found"},
                sources=["No commute data available"],
            )

        # Get commute times to all tech parks (peak driving)
        commutes = await conn.fetch(
            """SELECT ct.duration_min, ct.distance_km, ct.mode, ct.route_summary,
                      tp.name as tech_park, tp.employee_estimate,
                      ST_Y(tp.geog::geometry) as tp_lat, ST_X(tp.geog::geometry) as tp_lon
               FROM commute_times ct
               JOIN tech_parks tp ON ct.tech_park_id = tp.id
               WHERE ct.neighborhood_id = $1 AND ct.mode = 'car_peak'
               ORDER BY ct.duration_min
               LIMIT 10""",
            neighborhood["id"],
        )

        # Get off-peak and no-traffic times for comparison
        offpeak = await conn.fetch(
            """SELECT ct.duration_min, tp.name as tech_park
               FROM commute_times ct
               JOIN tech_parks tp ON ct.tech_park_id = tp.id
               WHERE ct.neighborhood_id = $1 AND ct.mode = 'car_offpeak'
               ORDER BY ct.duration_min""",
            neighborhood["id"],
        )

        no_traffic = await conn.fetch(
            """SELECT ct.duration_min, tp.name as tech_park
               FROM commute_times ct
               JOIN tech_parks tp ON ct.tech_park_id = tp.id
               WHERE ct.neighborhood_id = $1 AND ct.mode = 'car_no_traffic'
               ORDER BY ct.duration_min""",
            neighborhood["id"],
        )

    if not commutes:
        return ScoreResult(
            score=50.0, label="Average", data_confidence="low",
            breakdown={"note": "No commute data for this neighborhood. Run: python -m app.pipelines.runner fetch --commute"},
            sources=["Commute data not yet fetched"],
        )

    offpeak_map = {r["tech_park"]: float(r["duration_min"]) for r in offpeak}
    no_traffic_map = {r["tech_park"]: float(r["duration_min"]) for r in no_traffic}

    # Weighted score: average of top 3 nearest tech parks (by commute time)
    # Weighted by employee count (larger parks matter more)
    top_3 = commutes[:3]
    total_weight = sum(r["employee_estimate"] or 1 for r in top_3)
    weighted_score = sum(
        _commute_score(float(r["duration_min"])) * (r["employee_estimate"] or 1) / total_weight
        for r in top_3
    )
    final_score = round(min(max(weighted_score, 0), 100), 1)

    details = []
    for r in commutes[:5]:
        peak_min = float(r["duration_min"])
        _offpeak_min = offpeak_map.get(r["tech_park"], peak_min * 0.7)
        base_min = no_traffic_map.get(r["tech_park"], peak_min * 0.6)
        traffic_multiplier = round(peak_min / base_min, 1) if base_min > 0 else 1.0
        details.append(NearbyDetail(
            name=f"{r['tech_park']}: {base_min:.0f}min base → {peak_min:.0f}min peak ({traffic_multiplier}x traffic)",
            distance_km=round(r["distance_km"], 1),
            category="tech_park_commute",
            latitude=r["tp_lat"],
            longitude=r["tp_lon"],
        ))

    nearest = commutes[0]
    nearest_base = no_traffic_map.get(nearest["tech_park"])
    nearest_peak = float(nearest["duration_min"])
    nearest_offpeak = offpeak_map.get(nearest["tech_park"])

    # Marketing lie detection: listings typically show no-traffic time (Google default)
    marketing_claim = nearest_base
    lie_factor = round(nearest_peak / marketing_claim, 2) if marketing_claim else None

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details,
        breakdown={
            "methodology": "Google Maps Distance Matrix API — with and without traffic",
            "neighborhood": neighborhood["name"],
            "nearest_tech_park": nearest["tech_park"],
            "nearest_no_traffic_min": nearest_base,
            "nearest_peak_traffic_min": nearest_peak,
            "nearest_offpeak_min": nearest_offpeak,
            "traffic_multiplier": round(nearest_peak / nearest_base, 2) if nearest_base else None,
            "nearest_distance_km": float(nearest["distance_km"]),
            "tech_parks_scored": len(top_3),
            "weighted_by": "employee count at each tech park",
            "marketing_claim_min": marketing_claim,
            "reality_peak_min": nearest_peak,
            "lie_factor": lie_factor,
        },
        sources=SOURCES,
    )
