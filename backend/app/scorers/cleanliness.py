"""
Neighborhood Cleanliness Score (0-100)

METHODOLOGY: Slum proximity + BBMP waste infrastructure access

Sources:
  - Bengaluru Slums Map (data.opencity.in) — CNN satellite imagery, DN deprivation 0-245
  - BBMP Dry Waste Collection Centres — 336 locations
  - BBMP Waste Processing Plants — 8 locations
  - BBMP Landfill Locations — 3 locations (negative signal)
  - BBMP Biomethanisation Plants — 11 locations

Scoring formula (weighted):
  1. Slum proximity penalty (40%): count + deprivation-weighted density within 2km
  2. Waste infrastructure access (30%): dry waste centre proximity + density
  3. Landfill proximity penalty (15%): closer = worse (odor, pollution, pests)
  4. Waste processing coverage (15%): modern processing/biomethanisation access
"""

from app.db import get_pool
from app.models import NearbyDetail, ScoreResult, score_label

SOURCES = [
    "Bengaluru Slums Map — data.opencity.in (CNN satellite, DN deprivation index)",
    "BBMP Dry Waste Collection Centres — data.opencity.in (336 locations)",
    "BBMP Waste Processing Plants — data.opencity.in",
    "BBMP Landfill Locations — data.opencity.in (negative proximity signal)",
    "BBMP Biomethanisation Plants — data.opencity.in",
]

SLUM_RADIUS_M = 2000
WASTE_SEARCH_RADIUS_M = 5000


def _slum_density_score(count: int, avg_dn: float) -> float:
    """Higher count + higher deprivation = lower score."""
    if count == 0:
        return 100.0
    # Normalize DN to 0-1 severity (higher DN = worse)
    severity = min(avg_dn / 245.0, 1.0)
    # Density penalty: each slum polygon within 2km costs points, weighted by severity
    penalty = count * (0.5 + 0.5 * severity)
    # Scale: 0 slums = 100, ~50+ weighted slums = 0
    return max(0.0, min(100.0, 100.0 - penalty * 2.0))


def _waste_access_score(nearest_m: float, count_5km: int) -> float:
    """MOHUA-style proximity score for dry waste centres.
    Bangalore has ~336 centres across ~741 sq km, so avg spacing is ~1.5km.
    Thresholds calibrated to this density."""
    if nearest_m <= 500:
        base = 100.0
    elif nearest_m <= 1500:
        base = 100.0 - 20.0 * (nearest_m - 500) / 1000
    elif nearest_m <= 3000:
        base = 80.0 - 30.0 * (nearest_m - 1500) / 1500
    elif nearest_m <= 5000:
        base = 50.0 - 20.0 * (nearest_m - 3000) / 2000
    else:
        base = max(10.0, 30.0 - 10.0 * (nearest_m - 5000) / 3000)

    density_bonus = min(count_5km * 2.0, 20.0)
    return min(100.0, base + density_bonus)


def _landfill_penalty_score(nearest_m: float) -> float:
    """Closer to landfill = worse. Inverted scoring."""
    if nearest_m < 1000:
        return 0.0
    if nearest_m < 2000:
        return 25.0 * (nearest_m - 1000) / 1000
    if nearest_m < 3000:
        return 25.0 + 25.0 * (nearest_m - 2000) / 1000
    if nearest_m < 5000:
        return 50.0 + 25.0 * (nearest_m - 3000) / 2000
    return 100.0


def _processing_score(nearest_m: float) -> float:
    """Proximity to waste processing or biomethanisation plant."""
    if nearest_m <= 2000:
        return 100.0
    if nearest_m <= 5000:
        return 100.0 - 50.0 * (nearest_m - 2000) / 3000
    if nearest_m <= 10000:
        return 50.0 - 25.0 * (nearest_m - 5000) / 5000
    return 25.0


async def compute_cleanliness_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        # 1. Slum proximity: count and average deprivation within 2km
        slum_stats = await conn.fetchrow(
            """SELECT COUNT(*) as cnt,
                      COALESCE(AVG(deprivation_dn), 0) as avg_dn,
                      COALESCE(MIN(ST_Distance(centroid_geog, ST_Point($1, $2)::geography)), 99999) as nearest_m
               FROM slum_zones
               WHERE ST_DWithin(centroid_geog, ST_Point($1, $2)::geography, $3)""",
            lon,
            lat,
            SLUM_RADIUS_M,
        )

        # 2. Nearest dry waste centre + count within 2km
        dry_waste = await conn.fetchrow(
            """SELECT name,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as dist_m,
                      ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon
               FROM waste_infrastructure
               WHERE type = 'dry_waste_centre'
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 1""",
            lon,
            lat,
        )
        dry_waste_count = await conn.fetchval(
            """SELECT COUNT(*) FROM waste_infrastructure
               WHERE type = 'dry_waste_centre'
               AND ST_DWithin(geog, ST_Point($1, $2)::geography, $3)""",
            lon,
            lat,
            WASTE_SEARCH_RADIUS_M,
        )

        # 3. Nearest landfill
        landfill = await conn.fetchrow(
            """SELECT name,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as dist_m,
                      ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon
               FROM waste_infrastructure
               WHERE type = 'landfill'
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 1""",
            lon,
            lat,
        )

        # 4. Nearest processing plant or biomethanisation
        processing = await conn.fetchrow(
            """SELECT name, type,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as dist_m,
                      ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon
               FROM waste_infrastructure
               WHERE type IN ('waste_processing', 'biomethanisation')
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 1""",
            lon,
            lat,
        )

    slum_count = int(slum_stats["cnt"]) if slum_stats else 0
    avg_dn = float(slum_stats["avg_dn"]) if slum_stats else 0
    nearest_slum_m = float(slum_stats["nearest_m"]) if slum_stats else 99999

    nearest_dry_waste_m = float(dry_waste["dist_m"]) if dry_waste else 99999
    nearest_landfill_m = float(landfill["dist_m"]) if landfill else 99999
    nearest_processing_m = float(processing["dist_m"]) if processing else 99999

    s1 = _slum_density_score(slum_count, avg_dn)
    s2 = _waste_access_score(nearest_dry_waste_m, dry_waste_count or 0)
    s3 = _landfill_penalty_score(nearest_landfill_m)
    s4 = _processing_score(nearest_processing_m)

    final = round(0.40 * s1 + 0.30 * s2 + 0.15 * s3 + 0.15 * s4, 1)
    final = max(0.0, min(100.0, final))

    details = []
    if dry_waste:
        details.append(
            NearbyDetail(
                name=f"Dry Waste Centre: {dry_waste['name']}",
                distance_km=round(nearest_dry_waste_m / 1000, 2),
                category="dry_waste_centre",
                latitude=dry_waste["lat"],
                longitude=dry_waste["lon"],
            )
        )
    if landfill:
        details.append(
            NearbyDetail(
                name=f"Landfill: {landfill['name']}",
                distance_km=round(nearest_landfill_m / 1000, 2),
                category="landfill",
                latitude=landfill["lat"],
                longitude=landfill["lon"],
            )
        )
    if processing:
        details.append(
            NearbyDetail(
                name=f"{processing['type'].replace('_', ' ').title()}: {processing['name']}",
                distance_km=round(nearest_processing_m / 1000, 2),
                category="waste_processing",
                latitude=processing["lat"],
                longitude=processing["lon"],
            )
        )

    return ScoreResult(
        score=final,
        label=score_label(final),
        details=details,
        breakdown={
            "methodology": "Slum proximity (CNN deprivation) + BBMP waste infrastructure access",
            "slum_count_2km": slum_count,
            "avg_deprivation_dn": round(avg_dn, 1),
            "nearest_slum_m": round(nearest_slum_m, 0) if nearest_slum_m < 90000 else None,
            "slum_density_score": round(s1, 1),
            "nearest_dry_waste_m": round(nearest_dry_waste_m, 0) if nearest_dry_waste_m < 90000 else None,
            "dry_waste_centres_5km": dry_waste_count or 0,
            "waste_access_score": round(s2, 1),
            "nearest_landfill_m": round(nearest_landfill_m, 0) if nearest_landfill_m < 90000 else None,
            "landfill_penalty_score": round(s3, 1),
            "nearest_processing_m": round(nearest_processing_m, 0) if nearest_processing_m < 90000 else None,
            "processing_score": round(s4, 1),
        },
        sources=SOURCES,
    )
