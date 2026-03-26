"""
Flood Risk Score (0-100)

METHODOLOGY: BBMP Flood Ward Classification + KSNDMC Elevation Data
Source: data.opencity.in — BBMP Flooding Locations (CC BY Public Domain)
        BBMP 210 Flood-Prone Spots Report (Times Now / Deccan Herald 2025)
        KSNDMC — Karnataka State Natural Disaster Monitoring Centre
        Google Elevation API — terrain elevation data

Higher score = LOWER flood risk (safer).
Score inverted: 100 = no flood risk, 0 = severe flood risk.

Factors:
  1. BBMP flood spot count within neighborhood radius
  2. Historical flood events (documented by BBMP/media)
  3. Drainage quality (BBMP stormwater drain classification)
  4. Terrain elevation (lower elevation = higher risk)
  5. BBMP flood ward designation
"""

from app.db import get_pool
from app.models import ScoreResult

SOURCES = [
    "BBMP Flooding Locations — data.opencity.in (Public Domain, updated Nov 2025)",
    "BBMP 210 Flood-Prone Spots Report (2025) — Times Now / Deccan Herald",
    "KSNDMC — Karnataka State Natural Disaster Monitoring Centre",
    "Google Elevation API — terrain elevation",
    "Koramangala-Challaghatta (KC) & Hebbal valley flood risk mapping",
]


async def compute_flood_risk_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT fr.risk_level, fr.flood_history_events, fr.elevation_m,
                      fr.drainage_quality, fr.waterlogging_prone_spots,
                      fr.bbmp_flood_ward, fr.score,
                      n.name as neighborhood
               FROM flood_risk fr
               JOIN neighborhoods n ON fr.neighborhood_id = n.id
               ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

    if not row:
        return ScoreResult(
            score=70.0, label="Good", data_confidence="low",
            breakdown={"note": "No flood data available for this location"},
            sources=["No BBMP flood data within range"],
        )

    score = float(row["score"])
    risk_level = row["risk_level"]

    risk_labels = {
        "low": "Low Risk",
        "moderate": "Moderate Risk",
        "high": "High Risk",
        "very_high": "Very High Risk — Flood Zone",
    }

    BANGALORE_AVG_ELEVATION_M = 920
    raw_elev = row["elevation_m"]
    elevation_m = round(raw_elev) if raw_elev is not None else None

    if elevation_m is not None:
        if elevation_m > 930:
            elevation_insight = f"Well above Bangalore avg ({BANGALORE_AVG_ELEVATION_M}m) — natural drainage advantage, lower flood risk"
        elif elevation_m >= 910:
            elevation_insight = f"Near Bangalore avg elevation ({BANGALORE_AVG_ELEVATION_M}m) — typical flood risk for the city"
        elif elevation_m >= 880:
            elevation_insight = f"Below city average ({BANGALORE_AVG_ELEVATION_M}m) — check drainage infrastructure, moderate flood concern"
        else:
            elevation_insight = f"Significantly below avg ({BANGALORE_AVG_ELEVATION_M}m) — low-lying area, higher waterlogging risk"
    else:
        elevation_insight = None

    return ScoreResult(
        score=score,
        label=risk_labels.get(risk_level, risk_level),
        breakdown={
            "methodology": "BBMP flood ward classification + elevation + historical events",
            "neighborhood": row["neighborhood"],
            "risk_level": risk_level,
            "flood_history_events": row["flood_history_events"],
            "elevation_m": elevation_m,
            "elevation_insight": elevation_insight,
            "drainage_quality": row["drainage_quality"],
            "bbmp_flood_ward": row["bbmp_flood_ward"],
            "waterlogging_spots": row["waterlogging_prone_spots"],
        },
        sources=SOURCES,
    )
