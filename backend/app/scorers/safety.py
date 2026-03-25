"""
Safety Score (0-100)

METHODOLOGY: MOHUA Ease of Living Index — Safety & Security Pillar
Source: smartcities.gov.in/Ease_of_Living_Index (MOHUA 2020)
        smartnet.niua.org/safety-and-security-index
        NARI 2025 — National Annual Report & Index on Women's Safety (NCW + Pvalue Analytics)

EoLI Safety Pillar uses 4 indicators (3 core + 1 supporting):
  1. Surveillance coverage (CCTV density per sq km)
  2. Crime incidence rate (per 100K population, NCRB methodology)
  3. Crimes against women proxy (from zone data)
  4. Police station accessibility

Equal weights (0.25 each) — MOHUA does not publish relative weights
for sub-indicators within the Safety & Security pillar.

Crime rate normalization uses percentile ranking against Bangalore city
zones rather than arbitrary min-max scaling.
"""

from app.db import get_pool
from app.models import ScoreResult, NearbyDetail, score_label

# MOHUA EoLI Safety Pillar — 4 equal-weight indicators
INDICATOR_WEIGHT = 0.25

# MOHUA EoLI benchmark: 100% CCTV coverage of streets/junctions
EOLI_CCTV_BENCHMARK_PER_SQKM = 10.0

SOURCES = [
    "MOHUA Ease of Living Index — Safety & Security Pillar (smartcities.gov.in)",
    "NARI 2025 — National Commission for Women + Pvalue Analytics",
    "Karnataka Crime Data 2024 — data.opencity.in (NCRB methodology)",
    "Police Station Locations — data.opencity.in (CC BY 4.0)",
    "BBMP Zone-wise Streetlight Data — data.opencity.in",
]


async def compute_safety_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        nearest_stations = await conn.fetch(
            """SELECT name, COALESCE(tags->>'type', 'police_station') as type,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM pois
               WHERE category = 'police'
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 5""",
            lon, lat,
        )

        zone = await conn.fetchrow(
            """SELECT zone_name, crime_rate_per_100k, streetlight_pct,
                      cctv_density_per_sqkm, police_density_per_sqkm, score
               FROM safety_zones
               ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography)
               LIMIT 1""",
            lon, lat,
        )

        all_zones = await conn.fetch(
            "SELECT crime_rate_per_100k FROM safety_zones"
        )

    if not zone:
        return ScoreResult(score=50.0, label="Average", data_confidence="low", sources=["No safety data"])

    # --- Indicator 1: Surveillance coverage (CCTV density) ---
    # EoLI formula: (covered / total) * 100; we use density vs benchmark
    cctv_score = min(zone["cctv_density_per_sqkm"] / EOLI_CCTV_BENCHMARK_PER_SQKM, 1.0) * 100

    # --- Indicator 2: Crime incidence rate (NCRB percentile) ---
    # Percentile ranking: what % of zones have higher crime than this zone
    crime_rates = sorted([r["crime_rate_per_100k"] for r in all_zones])
    zone_rate = zone["crime_rate_per_100k"]
    zones_with_higher = sum(1 for r in crime_rates if r > zone_rate)
    crime_percentile_score = (zones_with_higher / max(len(crime_rates), 1)) * 100

    # --- Indicator 3: Streetlight coverage (proxy for women's safety / NARI) ---
    # NARI 2025: poor lighting is top concern for 40% of urban women
    streetlight_score = min(zone["streetlight_pct"] / 80.0, 1.0) * 100

    # --- Indicator 4: Police station accessibility ---
    nearest_dist = float(nearest_stations[0]["distance_km"]) if nearest_stations else 10.0
    stations_within_2km = sum(1 for s in nearest_stations if s["distance_km"] <= 2.0)

    # TOD-style decay: optimal within 500m, acceptable within 2km
    if nearest_dist <= 0.5:
        police_access = 100
    elif nearest_dist <= 2.0:
        police_access = 100 - 50 * (nearest_dist - 0.5) / 1.5
    elif nearest_dist <= 5.0:
        police_access = 50 - 50 * (nearest_dist - 2.0) / 3.0
    else:
        police_access = 0
    police_access = min(police_access + min(stations_within_2km * 5, 15), 100)

    # --- Composite: equal weights per EoLI methodology ---
    final_score = round(min(max(
        INDICATOR_WEIGHT * cctv_score
        + INDICATOR_WEIGHT * crime_percentile_score
        + INDICATOR_WEIGHT * streetlight_score
        + INDICATOR_WEIGHT * police_access,
        0), 100), 1)

    details = [
        NearbyDetail(
            name=s["name"], distance_km=round(s["distance_km"], 2),
            category="police_station",
            latitude=s["latitude"], longitude=s["longitude"],
        )
        for s in nearest_stations
    ]

    return ScoreResult(
        score=final_score, label=score_label(final_score), details=details,
        breakdown={
            "methodology": "MOHUA EoLI Safety Pillar — 4 equal-weight indicators",
            "surveillance_coverage": round(cctv_score, 1),
            "crime_rate_percentile": round(crime_percentile_score, 1),
            "streetlight_coverage": round(streetlight_score, 1),
            "police_accessibility": round(police_access, 1),
            "zone": zone["zone_name"],
            "crime_rate_per_100k": zone["crime_rate_per_100k"],
            "cctv_density_per_sqkm": zone["cctv_density_per_sqkm"],
            "nearest_police_station_km": round(nearest_dist, 2),
        },
        sources=SOURCES,
    )
