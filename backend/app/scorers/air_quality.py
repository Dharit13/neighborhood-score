"""
Air Quality Score (0-100)

METHODOLOGY: CPCB National Air Quality Index (2014)
Source: Central Pollution Control Board (cpcb.nic.in)
Reference: Nature Scientific Reports, Table 1 (doi:10.1038/s41598-025-00814-9)

Sub-index formula (linear interpolation between breakpoints):
    Ip = [(IHi - ILo) / (BPHi - BPLo)] * (Cp - BPLo) + ILo

Where Ip = sub-index, Cp = pollutant concentration,
BPHi/BPLo = breakpoint concentrations, IHi/ILo = AQI values.

The overall AQI is the worst (highest) sub-index among all pollutants.
Livability score = linear inversion: score = max(0, 100 - aqi/5).
AQI 0 = score 100 (best), AQI 500 = score 0 (worst).

Distance weighting uses inverse-distance weighting (IDW) across
nearest CPCB monitoring stations — standard spatial interpolation.
"""

import json

from app.db import get_pool
from app.config import CURATED_DIR
from app.models import ScoreResult, NearbyDetail, score_label

# CPCB PM2.5 breakpoints (24-hour avg, ug/m3)
# Source: cpcb.nic.in, data.gov.in AQI breakpoint dataset (Sep 2024)
CPCB_PM25_BREAKPOINTS = [
    (0,   30,  0,   50),   # Good
    (31,  60,  51,  100),  # Satisfactory
    (61,  90,  101, 200),  # Moderate
    (91,  120, 201, 300),  # Poor
    (121, 250, 301, 400),  # Very Poor
    (251, 500, 401, 500),  # Severe
]

# CPCB AQI categories — official classification
CPCB_AQI_CATEGORIES = [
    (0,   50,  "Good"),
    (51,  100, "Satisfactory"),
    (101, 200, "Moderate"),
    (201, 300, "Poor"),
    (301, 400, "Very Poor"),
    (401, 500, "Severe"),
]

SOURCES = [
    "CPCB National Air Quality Index (2014) — cpcb.nic.in",
    "Sub-index formula: Ip = [(IHi-ILo)/(BPHi-BPLo)] * (Cp-BPLo) + ILo",
    "PM2.5 breakpoints (ug/m3): Good 0-30, Satisfactory 31-60, Moderate 61-90, Poor 91-120",
    "Bengaluru CPCB monitoring stations — data.opencity.in (CC BY 4.0)",
    "Bengaluru Hourly Air Quality Reports — data.opencity.in (CC BY 4.0)",
]


def _load_hourly_data() -> dict | None:
    path = CURATED_DIR / "aqi_hourly.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _aqi_category(aqi: float) -> str:
    for lo, hi, label in CPCB_AQI_CATEGORIES:
        if lo <= aqi <= hi:
            return label
    return "Severe"


def _aqi_to_livability_score(aqi: float) -> float:
    """Linear inversion: AQI 0 -> 100, AQI 500 -> 0."""
    return max(0.0, min(100.0, 100.0 - (aqi / 5.0)))


async def compute_air_quality_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        nearest = await conn.fetch(
            """SELECT name, area, avg_aqi, primary_pollutant,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM aqi_stations
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 3""",
            lon, lat,
        )

    if not nearest:
        return ScoreResult(score=50.0, label="Average", data_confidence="low", sources=["No CPCB stations found"])

    # Inverse-distance weighting (IDW) — standard spatial interpolation
    weights = [1.0 / max(float(s["distance_km"]), 0.1) for s in nearest]
    total_w = sum(weights)
    weighted_aqi = sum(s["avg_aqi"] * w for s, w in zip(nearest, weights)) / total_w

    final_score = round(_aqi_to_livability_score(weighted_aqi), 1)

    details = [
        NearbyDetail(
            name=f"{s['name']} (AQI: {s['avg_aqi']}, {_aqi_category(s['avg_aqi'])}) - {s['primary_pollutant'] or 'PM2.5'}",
            distance_km=round(s["distance_km"], 2), category="aqi_station",
            latitude=s["latitude"], longitude=s["longitude"],
        )
        for s in nearest
    ]

    breakdown = {
        "methodology": "CPCB National AQI (2014) linear inversion",
        "weighted_aqi": round(weighted_aqi, 1),
        "aqi_category": _aqi_category(weighted_aqi),
        "nearest_station": nearest[0]["name"],
        "nearest_station_aqi": nearest[0]["avg_aqi"],
        "nearest_station_km": round(nearest[0]["distance_km"], 2),
        "stations_used": len(nearest),
        "interpolation": "inverse-distance weighting (IDW)",
    }

    hourly = _load_hourly_data()
    if hourly and hourly.get("stations"):
        station_name = nearest[0]["name"]
        for key in hourly["stations"]:
            if key.lower() in station_name.lower() or station_name.lower() in key.lower():
                periods = hourly["stations"][key]
                breakdown["time_of_day_aqi"] = {
                    "morning_rush": periods.get("morning_rush"),
                    "midday": periods.get("midday"),
                    "evening_rush": periods.get("evening_rush"),
                    "night": periods.get("night"),
                }
                break

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details,
        breakdown=breakdown,
        sources=SOURCES,
    )
