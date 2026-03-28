"""
Hospital Access Score (0-100)

METHODOLOGY: Indian Public Health Standards (IPHS) 2022
Source: nhm.gov.in IPHS 2022 Volume I & II (Ministry of Health & Family Welfare)

IPHS norms:
  - District Hospital: 1 bed per 1,000 population (essential), 2 beds (desirable)
  - Community Health Centre: 1 per 120,000 population (plains)
  - Primary Health Centre: 1 per 30,000 population (plains)
  - Urban CHC (metro city, 100 beds): serves 5 lakh+ population

Scoring combines:
  1. Proximity to nearest NABH-accredited hospital (50%)
  2. Bed density within 5km relative to IPHS essential norm (30%)
  3. Emergency access — nearest any-tier hospital (20%)
"""

import json
import re

from app.db import get_pool
from app.models import NearbyDetail, ScoreResult, score_label
from app.utils.geo import decay_score

_NOT_HOSPITAL_RE = re.compile(
    r"clinic|dental|ayurved|homeo|physio|aesthetic|diagnost|skin|hair|"
    r"wellness center|wellness centre|eye care|\blab\b|pharma|veterinar|"
    r"yoga|\bspa\b|salon|essentials|fertility|ivf|docsapp|medibuddy|"
    r"healthcare &|health care &|\bnursing\b|pathology|x.?ray|scan centre|"
    r"chemist|medical store|medical shop|vaccine center|tooth|residency|"
    r"dispensary",
    re.IGNORECASE,
)

_REAL_HOSPITAL_RE = re.compile(
    r"\bhospital\b|institute of|medical college|children.s hospital|"
    r"maternity|\besi\b|\besic\b|\buphc\b|\bphc\b|health cent|"
    r"\bgovt\b|government|victoria|bowring|minto|isolation|nimhans",
    re.IGNORECASE,
)

MIN_REVIEWS_UNKNOWN = 100

# IPHS 2022 norms
IPHS_BEDS_PER_1000_ESSENTIAL = 1
IPHS_BEDS_PER_1000_DESIRABLE = 2

# Estimated population within 5km in urban Bangalore (~200K-500K)
# Conservative estimate for scoring: 300K
ESTIMATED_POP_5KM = 300_000
IPHS_BEDS_NEEDED_5KM = ESTIMATED_POP_5KM * IPHS_BEDS_PER_1000_ESSENTIAL / 1000

SOURCES = [
    "IPHS 2022 — Indian Public Health Standards (nhm.gov.in)",
    "Norms: 1 bed/1000 pop (essential), 2 beds/1000 (desirable)",
    "NABH Portal (portal.nabh.co) — accreditation data",
    "BBMP Hospital List — data.opencity.in (CC BY 4.0)",
]


async def compute_hospital_score(lat: float, lon: float) -> ScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        nearest_nabh = await conn.fetch(
            """SELECT name, tags,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM pois
               WHERE category = 'hospital'
                 AND (tags->>'accreditation') IS NOT NULL
                 AND COALESCE((tags->>'tier')::int, 1) = 1
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 5""",
            lon,
            lat,
        )

        nearest_other_raw = await conn.fetch(
            """SELECT name, tags, rating, user_ratings_total,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM pois
               WHERE category = 'hospital'
                 AND ((tags->>'accreditation') IS NULL OR COALESCE((tags->>'tier')::int, 2) = 2)
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 25""",
            lon,
            lat,
        )
        nearest_other = []
        for h in nearest_other_raw:
            name = h["name"]
            if _NOT_HOSPITAL_RE.search(name):
                continue
            if _REAL_HOSPITAL_RE.search(name):
                nearest_other.append(h)
            elif (h["user_ratings_total"] or 0) >= MIN_REVIEWS_UNKNOWN:
                nearest_other.append(h)
            if len(nearest_other) >= 5:
                break

        total_beds_5km = await conn.fetchval(
            """SELECT COALESCE(SUM(COALESCE((tags->>'beds')::int, 0)), 0)
               FROM pois
               WHERE category = 'hospital'
                 AND ST_DWithin(geog, ST_Point($1, $2)::geography, 5000)""",
            lon,
            lat,
        )

    # --- Component 1: NABH proximity (50%) ---
    if nearest_nabh:
        nabh_proximity = decay_score(float(nearest_nabh[0]["distance_km"]), 1.0, 8.0) * 100
    else:
        nabh_proximity = 0.0

    # --- Component 2: Bed density vs IPHS norm (30%) ---
    bed_ratio = total_beds_5km / max(IPHS_BEDS_NEEDED_5KM, 1)
    bed_density_score = min(bed_ratio, 1.0) * 100

    # --- Component 3: Emergency access (20%) ---
    all_nearest = list(nearest_nabh) + list(nearest_other)
    all_nearest.sort(key=lambda x: x["distance_km"])
    if all_nearest:
        emergency_prox = decay_score(float(all_nearest[0]["distance_km"]), 1.0, 5.0) * 100
    else:
        emergency_prox = 0.0

    final_score = round(min(max(0.50 * nabh_proximity + 0.30 * bed_density_score + 0.20 * emergency_prox, 0), 100), 1)

    details = []
    seen = set()
    for h in all_nearest[:10]:
        if h["name"] in seen:
            continue
        seen.add(h["name"])
        tags = json.loads(h["tags"]) if isinstance(h["tags"], str) else (h["tags"] or {})
        accred = tags.get("accreditation")
        tier = tags.get("tier", 2)
        tier_label = accred if accred else ("Tier 1" if tier == 1 else "Hospital")
        beds = tags.get("beds", "N/A")
        specs = ", ".join((tags.get("specialties") or [])[:3])
        label = f"{h['name']} ({tier_label}, {beds} beds)"
        if specs:
            label += f" - {specs}"
        details.append(
            NearbyDetail(
                name=label,
                distance_km=round(h["distance_km"], 2),
                category=f"hospital_tier_{tier}",
                latitude=h["latitude"],
                longitude=h["longitude"],
            )
        )

    return ScoreResult(
        score=final_score,
        label=score_label(final_score),
        details=details[:8],
        breakdown={
            "methodology": "IPHS 2022 — bed density vs norm + NABH proximity",
            "nabh_hospital_proximity": round(nabh_proximity, 1),
            "bed_density_vs_iphs": round(bed_density_score, 1),
            "emergency_proximity": round(emergency_prox, 1),
            "total_beds_within_5km": total_beds_5km,
            "iphs_beds_needed_5km": IPHS_BEDS_NEEDED_5KM,
            "bed_ratio": round(bed_ratio, 2),
        },
        sources=SOURCES,
    )
