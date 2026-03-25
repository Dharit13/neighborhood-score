"""
Noise Score (0-100)

METHODOLOGY: CPCB noise monitoring + flight path + highway proximity
Source: CPCB real-time noise monitoring (data.gov.in) — real dB measurements
        DGCA / BIAL — KIA approach corridor noise studies (64-70 dB documented)
        The Hindu (Apr 2025) — HAL Airport flight path obstructions
        Highway proximity: NH44, NH75, ORR, NICE Road

Higher score = QUIETER area (inverted noise level).

CPCB noise standards (dB Leq):
  Residential: Day 55, Night 45
  Commercial:  Day 65, Night 55
  Industrial:  Day 75, Night 70
  Silence:     Day 50, Night 40
"""

from app.db import get_pool
from app.models import ScoreResult, score_label

SOURCES = [
    "CPCB Noise Monitoring Stations — data.gov.in (Feb 2025)",
    "DGCA / BIAL — Kempegowda International Airport noise studies",
    "HAL Airport flight path — The Hindu (Apr 2025)",
    "Highway proximity: NH44, NH75, ORR, NICE Road, Mysore Road",
    "CPCB National Ambient Noise Monitoring Network",
]


async def compute_noise_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT nz.airport_flight_path, nz.highway_proximity_km,
                      nz.construction_zones_active, nz.avg_noise_db_estimate,
                      nz.noise_label, nz.score,
                      n.name as neighborhood
               FROM noise_zones nz
               JOIN neighborhoods n ON nz.neighborhood_id = n.id
               ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

    if not row:
        return ScoreResult(
            score=60.0, label="Good", data_confidence="low",
            breakdown={"note": "No noise data available"},
            sources=["No noise data within range"],
        )

    score = round(float(row["score"]), 1)
    noise_db = round(float(row["avg_noise_db_estimate"]), 1)

    highway_km = round(float(row["highway_proximity_km"]), 2)
    noise_factors = []
    if row["airport_flight_path"]:
        noise_factors.append("Under airport flight path")
    if highway_km <= 1.0:
        noise_factors.append(f"Highway {highway_km}km away")
    if row["construction_zones_active"] > 0:
        noise_factors.append(f"{row['construction_zones_active']} metro construction sites nearby")

    # CPCB compliance check
    cpcb_residential_day = 55
    exceeds_cpcb = noise_db > cpcb_residential_day

    return ScoreResult(
        score=score,
        label=row["noise_label"].replace("_", " ").title(),
        breakdown={
            "methodology": "CPCB noise monitoring + flight path + highway + construction",
            "neighborhood": row["neighborhood"],
            "avg_noise_db_estimate": noise_db,
            "noise_label": row["noise_label"],
            "cpcb_residential_standard_db": cpcb_residential_day,
            "exceeds_cpcb_residential": exceeds_cpcb,
            "airport_flight_path": row["airport_flight_path"],
            "highway_proximity_km": highway_km,
            "construction_zones_active": row["construction_zones_active"],
            "noise_factors": noise_factors,
        },
        sources=SOURCES,
    )
