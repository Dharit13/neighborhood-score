from fastapi import APIRouter, HTTPException
from app.db import get_pool
from app.models import (
    LocationInput, NeighborhoodScoreResponse, AIVerification,
    NeighborhoodRank, RentVsBuyArea, WardInfo, score_label,
    ClaimInput, ClaimVerification, ClaimVerificationResponse,
)
from app.utils.geo import geocode_address, reverse_geocode, actual_walk_time, haversine_km
from app.scorers.walkability import compute_walkability_score
from app.scorers.safety import compute_safety_score
from app.scorers.hospital import compute_hospital_score
from app.scorers.school import compute_school_score
from app.scorers.transit import compute_transit_score
from app.scorers.builder import compute_builder_score
from app.scorers.air_quality import compute_air_quality_score
from app.scorers.water_supply import compute_water_supply_score
from app.scorers.power import compute_power_score
from app.scorers.future_infra import compute_future_infra_score
from app.scorers.property_price import compute_property_price_info
from app.scorers.flood_risk import compute_flood_risk_score
from app.scorers.commute import compute_commute_score
from app.scorers.delivery_coverage import compute_delivery_coverage_score
from app.scorers.noise import compute_noise_score
from app.scorers.business_opportunity import compute_business_opportunity_score
from app.scorers.cleanliness import compute_cleanliness_score
from app.config import SCORE_WEIGHTS, CURATED_DIR
import json as _json
import logging as _logging
from math import radians as _rad, sin as _sin, cos as _cos, sqrt as _sqrt, atan2 as _atan2

router = APIRouter(prefix="/api", tags=["scores"])

_score_cache: dict[str, dict] = {}
_score_cache_coords: list[tuple[str, float, float]] = []

def _load_score_cache():
    """Load precomputed full score responses from disk."""
    cache_file = CURATED_DIR / "precomputed_scores.json"
    if not cache_file.exists():
        return
    try:
        with open(cache_file) as f:
            data = _json.load(f)
        for entry in data.get("neighborhoods", []):
            name = entry.get("name", "")
            if name:
                _score_cache[name.lower()] = entry
                _score_cache_coords.append((name.lower(), entry["latitude"], entry["longitude"]))
        _logging.getLogger(__name__).info(f"Score cache loaded: {len(_score_cache)} neighborhoods")
    except Exception as e:
        _logging.getLogger(__name__).warning(f"Failed to load score cache: {e}")

_load_score_cache()


def _find_cached_score(lat: float, lon: float, address: str | None = None) -> dict | None:
    """Look up a cached score by address name or proximity (within 1km)."""
    if address:
        name_key = address.split(",")[0].strip().lower()
        if name_key in _score_cache:
            return _score_cache[name_key]

    for name, clat, clon in _score_cache_coords:
        dlat = lat - clat
        dlon = lon - clon
        if _sqrt(dlat * dlat + dlon * dlon) * 111 < 1.0:
            return _score_cache[name]
    return None


async def _get_ai_verification(lat: float, lon: float) -> AIVerification | None:
    """Look up cached AI verification for the nearest neighborhood within 5km."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT nv.confidence, nv.flags, nv.narrative, nv.verified_at, nv.model_used
                   FROM neighborhood_verification nv
                   JOIN neighborhoods n ON nv.neighborhood_id = n.id
                   WHERE ST_DWithin(n.center_geog, ST_Point($1, $2)::geography, 5000)
                   ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
                   LIMIT 1""",
                lon, lat,
            )
        if row:
            import json as _json
            flags_raw = row["flags"]
            if isinstance(flags_raw, str):
                try:
                    flags_raw = _json.loads(flags_raw)
                except _json.JSONDecodeError:
                    flags_raw = [flags_raw]
            if not isinstance(flags_raw, list):
                flags_raw = []

            # Parse structured narrative (JSON) or plain text
            narrative_str = row["narrative"] or ""
            verdict, pros, cons, best_for, avoid_if = "", [], [], "", ""
            lifestyle_tags_raw: list[dict] = []
            try:
                narrative_obj = _json.loads(narrative_str)
                if isinstance(narrative_obj, dict):
                    verdict = narrative_obj.get("verdict", "")
                    pros = narrative_obj.get("pros", [])
                    cons = narrative_obj.get("cons", [])
                    best_for = narrative_obj.get("best_for", "")
                    avoid_if = narrative_obj.get("avoid_if", "")
                    lifestyle_tags_raw = narrative_obj.get("lifestyle_tags", [])
                    narrative_str = verdict
            except (_json.JSONDecodeError, TypeError):
                pass

            from app.models import LifestyleTag
            lifestyle_tags = [
                LifestyleTag(
                    category=t.get("category", ""),
                    label=t.get("label", ""),
                    detail=t.get("detail", ""),
                )
                for t in lifestyle_tags_raw if isinstance(t, dict)
            ]

            return AIVerification(
                confidence=row["confidence"],
                narrative=narrative_str,
                verdict=verdict,
                pros=pros,
                cons=cons,
                best_for=best_for,
                avoid_if=avoid_if,
                flags=flags_raw,
                lifestyle_tags=lifestyle_tags,
                verified_at=row["verified_at"],
                model_used=row["model_used"],
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"AI verification lookup failed: {e}")
    return None


async def _get_neighborhood_rankings(exclude_name: str | None = None) -> tuple[list[NeighborhoodRank], list[NeighborhoodRank]]:
    """Rank all neighborhoods using pre-seeded zone scores. No external API calls."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT n.name,
                       sz.score as safety_score, sz.crime_rate_per_100k,
                       wz.score as walkability_score,
                       wtz.score as water_score,
                       pz.score as power_score,
                       fr.score as flood_score, fr.elevation_m,
                       pp.affordability_score, pp.avg_price_sqft, pp.yoy_growth_pct
                FROM neighborhoods n
                LEFT JOIN safety_zones sz ON sz.neighborhood_id = n.id
                LEFT JOIN walkability_zones wz ON wz.neighborhood_id = n.id
                LEFT JOIN water_zones wtz ON wtz.neighborhood_id = n.id
                LEFT JOIN power_zones pz ON pz.neighborhood_id = n.id
                LEFT JOIN flood_risk fr ON fr.neighborhood_id = n.id
                LEFT JOIN property_prices pp ON pp.neighborhood_id = n.id
            """)

        if not rows:
            return [], []

        scored = []
        for r in rows:
            name = r["name"]
            if name == exclude_name:
                continue

            safety = float(r["safety_score"] or 50)
            walk = float(r["walkability_score"] or 50)
            water = float(r["water_score"] or 50)
            power = float(r["power_score"] or 50)
            flood = float(r["flood_score"] or 50)
            afford = float(r["affordability_score"] or 50)

            composite = (
                0.25 * safety + 0.15 * walk + 0.15 * water
                + 0.10 * power + 0.20 * flood + 0.15 * afford
            )

            highlights = []
            if safety >= 75:
                highlights.append("Safe neighborhood")
            elif safety < 40:
                highlights.append("Higher crime rate")
            if flood >= 70:
                highlights.append("Low flood risk")
            elif flood < 40:
                highlights.append("Flood-prone area")
            if afford >= 60:
                highlights.append("Affordable")
            elif afford < 15:
                highlights.append("Very expensive")
            if walk >= 75:
                highlights.append("Very walkable")
            if water >= 75:
                highlights.append("Reliable water supply")
            elif water < 40:
                highlights.append("Water supply issues")
            price = r["avg_price_sqft"]
            if price:
                highlights.append(f"~₹{int(price):,}/sqft")
            growth = r["yoy_growth_pct"]
            if growth and growth > 10:
                highlights.append(f"+{round(float(growth), 1)}% YoY growth")

            scored.append((name, round(composite, 1), highlights))

        scored.sort(key=lambda x: x[1], reverse=True)

        top_3 = [
            NeighborhoodRank(name=s[0], score=s[1], label=score_label(s[1]), highlights=s[2][:3])
            for s in scored[:3]
        ]
        bottom_3 = [
            NeighborhoodRank(name=s[0], score=s[1], label=score_label(s[1]), highlights=s[2][:3])
            for s in scored[-3:]
        ]
        return top_3, bottom_3

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Neighborhood ranking failed: {e}")
        return [], []


async def _get_rent_vs_buy_rankings() -> tuple[list[RentVsBuyArea], list[RentVsBuyArea]]:
    """Rank neighborhoods by rent-vs-buy using EMI-to-rent ratio from pre-seeded data."""
    EMI_PER_LAKH_20YR = 836

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT area, avg_price_sqft, avg_2bhk_lakh, avg_2bhk_rent,
                       rental_yield_pct
                FROM property_prices
                WHERE avg_2bhk_rent > 0 AND avg_2bhk_lakh > 0
            """)

        if not rows:
            return [], []

        areas = []
        for r in rows:
            rent = int(r["avg_2bhk_rent"])
            lakh = float(r["avg_2bhk_lakh"])
            emi = round(lakh * EMI_PER_LAKH_20YR)
            ratio = round(emi / rent, 2) if rent > 0 else 99
            yield_pct = round(float(r["rental_yield_pct"] or 0), 1)

            if ratio > 2.5:
                rec = "Rent"
            elif ratio > 1.5:
                rec = "Rent (buy if 7+ yr stay)"
            elif ratio > 0.8:
                rec = "Buy"
            else:
                rec = "Strong Buy"

            areas.append(RentVsBuyArea(
                area=r["area"],
                recommendation=rec,
                avg_2bhk_rent=rent,
                monthly_emi=emi,
                emi_rent_ratio=ratio,
                rental_yield_pct=yield_pct,
                avg_price_sqft=int(r["avg_price_sqft"]),
            ))

        buy_winners = sorted(
            [a for a in areas if a.emi_rent_ratio <= 1.5],
            key=lambda a: a.emi_rent_ratio,
        )[:3]

        rent_winners = sorted(
            [a for a in areas if a.emi_rent_ratio > 1.5],
            key=lambda a: a.emi_rent_ratio,
            reverse=True,
        )[:3]

        return buy_winners, rent_winners

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Rent vs buy ranking failed: {e}")
        return [], []


@router.get("/neighborhoods")
async def list_neighborhoods():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT name FROM neighborhoods ORDER BY name")
    return [r["name"] for r in rows]


@router.post("/scores", response_model=NeighborhoodScoreResponse)
async def get_neighborhood_scores(input: LocationInput):
    # Check cache first for instant responses
    if _score_cache:
        cache_lat = input.latitude
        cache_lon = input.longitude
        cache_addr = input.address
        if cache_lat is not None and cache_lon is not None:
            cached = _find_cached_score(cache_lat, cache_lon, cache_addr)
        elif cache_addr:
            cached = _find_cached_score(0, 0, cache_addr)
        else:
            cached = None
        if cached:
            if not cached.get("ai_verification"):
                lat_c = cached.get("latitude", 0)
                lon_c = cached.get("longitude", 0)
                ai = await _get_ai_verification(lat_c, lon_c)
                if ai:
                    cached = {**cached, "ai_verification": ai.model_dump()}
            return cached

    lat, lon = None, None

    user_provided_address = input.address
    if input.latitude is not None and input.longitude is not None:
        lat, lon = input.latitude, input.longitude
    elif input.address:
        user_provided_address = input.address
        result = geocode_address(input.address)
        if result is None:
            raise HTTPException(
                status_code=400,
                detail=f"Could not geocode address: '{input.address}'. Try a more specific Bangalore location.",
            )
        lat, lon = result
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either latitude/longitude or an address.",
        )

    reverse_addr = reverse_geocode(lat, lon)
    address = user_provided_address if user_provided_address else reverse_addr

    # All scorers are async — await each
    walkability = await compute_walkability_score(lat, lon)
    safety = await compute_safety_score(lat, lon)
    hospital = await compute_hospital_score(lat, lon)
    school = await compute_school_score(lat, lon)
    transit = await compute_transit_score(lat, lon)
    builder = await compute_builder_score(lat, lon, address, input.builder_name)
    air_quality = await compute_air_quality_score(lat, lon)
    water_supply = await compute_water_supply_score(lat, lon)
    power = await compute_power_score(lat, lon)
    future_infra = await compute_future_infra_score(lat, lon)
    property_prices = await compute_property_price_info(lat, lon)
    flood_risk = await compute_flood_risk_score(lat, lon)
    commute = await compute_commute_score(lat, lon)
    delivery = await compute_delivery_coverage_score(lat, lon)
    noise = await compute_noise_score(lat, lon)
    business_opp = await compute_business_opportunity_score(lat, lon)
    cleanliness = await compute_cleanliness_score(lat, lon)

    # Composite score using ANAROCK survey-derived weights (17 dimensions)
    composite = (
        SCORE_WEIGHTS.get("walkability", 0) * walkability.score
        + SCORE_WEIGHTS.get("safety", 0) * safety.score
        + SCORE_WEIGHTS.get("hospital_access", 0) * hospital.score
        + SCORE_WEIGHTS.get("school_access", 0) * school.score
        + SCORE_WEIGHTS.get("transit_access", 0) * transit.score
        + SCORE_WEIGHTS.get("builder_reputation", 0) * builder.score
        + SCORE_WEIGHTS.get("air_quality", 0) * air_quality.score
        + SCORE_WEIGHTS.get("water_supply", 0) * water_supply.score
        + SCORE_WEIGHTS.get("power_reliability", 0) * power.score
        + SCORE_WEIGHTS.get("future_infrastructure", 0) * future_infra.score
        + SCORE_WEIGHTS.get("affordability", 0) * property_prices.score
        + SCORE_WEIGHTS.get("flood_risk", 0) * flood_risk.score
        + SCORE_WEIGHTS.get("commute", 0) * commute.score
        + SCORE_WEIGHTS.get("delivery_coverage", 0) * delivery.score
        + SCORE_WEIGHTS.get("noise", 0) * noise.score
        + SCORE_WEIGHTS.get("business_opportunity", 0) * business_opp.score
        + SCORE_WEIGHTS.get("cleanliness", 0) * cleanliness.score
    )
    composite = round(composite, 1)

    # Look up cached AI verification
    ai_verification = await _get_ai_verification(lat, lon)

    # Get neighborhood rankings (exclude the current one)
    current_area = property_prices.breakdown.get("area") if property_prices.breakdown else None
    recommended, to_avoid = await _get_neighborhood_rankings(exclude_name=current_area)
    best_buy, best_rent = await _get_rent_vs_buy_rankings()

    wards_covered: list[WardInfo] = []
    wards_total_pop: int | None = None
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            ward_rows = await conn.fetch(
                """SELECT DISTINCT ON (ward_name) ward_name, corporation, population,
                          ST_Distance(centroid_geog, ST_Point($1, $2)::geography) / 1000.0 as dist_km
                   FROM ward_mapping
                   WHERE centroid_geog IS NOT NULL
                     AND ST_DWithin(centroid_geog, ST_Point($1, $2)::geography, 5000)
                   ORDER BY ward_name, ST_Distance(centroid_geog, ST_Point($1, $2)::geography)""",
                lon, lat,
            )
            nearby = sorted(ward_rows, key=lambda r: r["dist_km"])
            for wr in nearby[:8]:
                wards_covered.append(WardInfo(
                    name=wr["ward_name"],
                    corporation=wr["corporation"],
                    population=wr["population"],
                    distance_km=round(float(wr["dist_km"]), 2),
                ))
            pops = [wr["population"] for wr in nearby[:8] if wr["population"]]
            wards_total_pop = sum(pops) if pops else None
    except Exception:
        pass

    return NeighborhoodScoreResponse(
        latitude=lat,
        longitude=lon,
        address=address,
        composite_score=composite,
        composite_label=score_label(composite),
        walkability=walkability,
        safety=safety,
        hospital_access=hospital,
        school_access=school,
        transit_access=transit,
        builder_reputation=builder,
        air_quality=air_quality,
        water_supply=water_supply,
        power_reliability=power,
        future_infrastructure=future_infra,
        property_prices=property_prices,
        flood_risk=flood_risk,
        commute=commute,
        delivery_coverage=delivery,
        noise=noise,
        business_opportunity=business_opp,
        cleanliness=cleanliness,
        ai_verification=ai_verification,
        recommended_neighborhoods=recommended,
        neighborhoods_to_avoid=to_avoid,
        best_to_buy=best_buy,
        best_to_rent=best_rent,
        wards_covered=wards_covered,
        wards_total_population=wards_total_pop,
    )


_prefetch_cache: dict | None = None


def _tod_proximity(distance_m: float) -> float:
    """MOHUA TOD scoring: 500m optimal, 800m acceptable, 2000m feeder."""
    if distance_m <= 500:
        return 100.0
    if distance_m <= 800:
        return 100 - 50 * (distance_m - 500) / 300
    if distance_m <= 2000:
        return 50 - 50 * (distance_m - 800) / 1200
    return 0.0


def _decay(dist_km: float, full_km: float, zero_km: float) -> float:
    if dist_km <= full_km:
        return 1.0
    if dist_km >= zero_km:
        return 0.0
    return 1.0 - (dist_km - full_km) / (zero_km - full_km)


@router.get("/prefetch")
async def prefetch_data():
    """Serve precomputed scores for map pins. Uses the same scores as /api/scores."""
    global _prefetch_cache
    if _prefetch_cache is not None:
        return _prefetch_cache

    # If precomputed scores exist, use them directly (exact match with /api/scores)
    if _score_cache:
        pool = await get_pool()
        async with pool.acquire() as conn:
            pp_rows = await conn.fetch(
                "SELECT area, avg_price_sqft, yoy_growth_pct FROM property_prices"
            )
        pp_map = {r["area"]: r for r in pp_rows}

        neighborhoods = []
        for entry in _score_cache.values():
            name = entry.get("name", entry.get("address", "").split(",")[0].strip())
            pp = pp_map.get(name, {})
            neighborhoods.append({
                "name": name,
                "latitude": entry["latitude"],
                "longitude": entry["longitude"],
                "score": entry["composite_score"],
                "label": entry["composite_label"],
                "avg_price_sqft": int(pp["avg_price_sqft"]) if pp.get("avg_price_sqft") else None,
                "yoy_growth_pct": round(float(pp["yoy_growth_pct"]), 1) if pp.get("yoy_growth_pct") else None,
                "safety_score": entry.get("safety", {}).get("score") if isinstance(entry.get("safety"), dict) else None,
            })

        # Deduplicate within 500m
        from math import radians, sin, cos, sqrt, atan2
        def _hav(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            return 6371000 * 2 * atan2(sqrt(a), sqrt(1 - a))

        neighborhoods.sort(key=lambda n: n["score"], reverse=True)
        deduped: list[dict] = []
        for n in neighborhoods:
            too_close = False
            for kept in deduped:
                if _hav(n["latitude"], n["longitude"], kept["latitude"], kept["longitude"]) < 500:
                    too_close = True
                    break
            if not too_close:
                deduped.append(n)

        _prefetch_cache = {"neighborhoods": deduped}
        return _prefetch_cache

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            # ── Base: neighborhoods + zone table scores (10 dims) ──
            base_rows = await conn.fetch("""
                SELECT n.id, n.name,
                       ST_Y(n.center_geog::geometry) as lat,
                       ST_X(n.center_geog::geometry) as lon,
                       sz.score as safety_score,
                       wz.score as walkability_score,
                       wtz.score as water_score,
                       pz.score as power_score,
                       fr.score as flood_score,
                       pp.affordability_score,
                       pp.avg_price_sqft,
                       pp.yoy_growth_pct,
                       nz.score as noise_score,
                       bo.score as business_score,
                       dc.coverage_score as delivery_score,
                       commute_agg.commute_score
                FROM neighborhoods n
                LEFT JOIN safety_zones sz ON sz.neighborhood_id = n.id
                LEFT JOIN walkability_zones wz ON wz.neighborhood_id = n.id
                LEFT JOIN water_zones wtz ON wtz.neighborhood_id = n.id
                LEFT JOIN power_zones pz ON pz.neighborhood_id = n.id
                LEFT JOIN flood_risk fr ON fr.neighborhood_id = n.id
                LEFT JOIN property_prices pp ON pp.neighborhood_id = n.id
                LEFT JOIN noise_zones nz ON nz.neighborhood_id = n.id
                LEFT JOIN business_opportunity bo ON bo.neighborhood_id = n.id
                LEFT JOIN delivery_coverage dc ON dc.neighborhood_id = n.id
                LEFT JOIN LATERAL (
                    SELECT CASE
                        WHEN avg_peak <= 20 THEN 100
                        WHEN avg_peak <= 30 THEN 100 - (avg_peak - 20) / 10.0 * 15
                        WHEN avg_peak <= 45 THEN 85 - (avg_peak - 30) / 15.0 * 20
                        WHEN avg_peak <= 60 THEN 65 - (avg_peak - 45) / 15.0 * 20
                        WHEN avg_peak <= 90 THEN 45 - (avg_peak - 60) / 30.0 * 20
                        ELSE GREATEST(5, 25 - (avg_peak - 90) / 30.0 * 20)
                    END as commute_score
                    FROM (
                        SELECT AVG(duration_min) as avg_peak
                        FROM (
                            SELECT duration_min FROM commute_times
                            WHERE neighborhood_id = n.id AND mode = 'car_peak'
                            ORDER BY duration_min LIMIT 3
                        ) top3
                    ) agg
                ) commute_agg ON true
                WHERE n.center_geog IS NOT NULL
            """)

            # ── Transit: nearest metro/bus/train per neighborhood ──
            transit_rows = await conn.fetch("""
                SELECT n.id,
                       COALESCE(metro.d, 99000) as metro_m,
                       COALESCE(bus.d, 99000) as bus_m,
                       COALESCE(train.d, 99000) as train_m
                FROM neighborhoods n
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(m.geog, n.center_geog) as d
                    FROM metro_stations m ORDER BY m.geog <-> n.center_geog LIMIT 1
                ) metro ON true
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(b.geog, n.center_geog) as d
                    FROM bus_stops b ORDER BY b.geog <-> n.center_geog LIMIT 1
                ) bus ON true
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(t.geog, n.center_geog) as d
                    FROM train_stations t ORDER BY t.geog <-> n.center_geog LIMIT 1
                ) train ON true
                WHERE n.center_geog IS NOT NULL
            """)
            transit_map: dict[int, float] = {}
            for tr in transit_rows:
                metro_m = float(tr["metro_m"])
                bus_m = float(tr["bus_m"])
                train_m = float(tr["train_m"])
                metro_s = _tod_proximity(metro_m)
                bus_s = _tod_proximity(bus_m)
                train_s = _tod_proximity(train_m)
                modal = sum(1 for d in (metro_m, bus_m, train_m) if d <= 800)
                multi_s = min(modal / 3.0, 1.0) * 100
                transit_map[tr["id"]] = round(
                    min(100, max(0, 0.35 * metro_s + 0.30 * bus_s + 0.20 * train_s + 0.15 * multi_s)), 1
                )

            # ── Air quality: IDW from 3 nearest AQI stations ──
            aqi_rows = await conn.fetch("""
                SELECT n.id, aqi_data.weighted_aqi
                FROM neighborhoods n
                LEFT JOIN LATERAL (
                    SELECT CASE WHEN sum_w > 0
                        THEN sum_wv / sum_w
                        ELSE NULL
                    END as weighted_aqi
                    FROM (
                        SELECT SUM(1.0 / GREATEST(ST_Distance(a.geog, n.center_geog) / 1000.0, 0.1)) as sum_w,
                               SUM(a.avg_aqi / GREATEST(ST_Distance(a.geog, n.center_geog) / 1000.0, 0.1)) as sum_wv
                        FROM (
                            SELECT geog, avg_aqi FROM aqi_stations
                            ORDER BY geog <-> n.center_geog LIMIT 3
                        ) a
                    ) idw
                ) aqi_data ON true
                WHERE n.center_geog IS NOT NULL
            """)
            aqi_map: dict[int, float] = {}
            for ar in aqi_rows:
                aqi_val = float(ar["weighted_aqi"]) if ar["weighted_aqi"] is not None else 100
                aqi_map[ar["id"]] = round(max(0, min(100, 100 - aqi_val / 5.0)), 1)

            # ── Hospital: NABH proximity + bed density + emergency ──
            hospital_rows = await conn.fetch("""
                SELECT n.id,
                       nabh.nearest_km as nabh_km,
                       COALESCE(beds.total, 0) as beds_5km,
                       COALESCE(any_h.nearest_km, 99) as any_km
                FROM neighborhoods n
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(p.geog, n.center_geog) / 1000.0 as nearest_km
                    FROM pois p
                    WHERE p.category = 'hospital'
                      AND (p.tags->>'accreditation') IS NOT NULL
                    ORDER BY p.geog <-> n.center_geog LIMIT 1
                ) nabh ON true
                LEFT JOIN LATERAL (
                    SELECT SUM(COALESCE((p.tags->>'beds')::int, 0)) as total
                    FROM pois p
                    WHERE p.category = 'hospital'
                      AND ST_DWithin(p.geog, n.center_geog, 5000)
                ) beds ON true
                LEFT JOIN LATERAL (
                    SELECT ST_Distance(p.geog, n.center_geog) / 1000.0 as nearest_km
                    FROM pois p
                    WHERE p.category = 'hospital'
                    ORDER BY p.geog <-> n.center_geog LIMIT 1
                ) any_h ON true
                WHERE n.center_geog IS NOT NULL
            """)
            hospital_map: dict[int, float] = {}
            for hr in hospital_rows:
                nabh_prox = _decay(float(hr["nabh_km"]) if hr["nabh_km"] is not None else 99, 1.0, 8.0) * 100
                bed_ratio = min(float(hr["beds_5km"]) / 300.0, 1.0) * 100
                emerg_prox = _decay(float(hr["any_km"]), 1.0, 5.0) * 100
                hospital_map[hr["id"]] = round(
                    min(100, 0.50 * nabh_prox + 0.30 * bed_ratio + 0.20 * emerg_prox), 1
                )

            # ── School: RTE compliance + quality + diversity ──
            school_rows = await conn.fetch("""
                SELECT n.id,
                       COALESCE(s1.cnt, 0) as within_1km,
                       COALESCE(s3.cnt, 0) as within_3km,
                       ranked.nearest_km as ranked_km,
                       COALESCE(ranked.top_3km, 0) as top_3km,
                       COALESCE(boards.board_count, 0) as board_count
                FROM neighborhoods n
                LEFT JOIN LATERAL (
                    SELECT COUNT(*)::int as cnt FROM pois
                    WHERE category = 'school' AND ST_DWithin(geog, n.center_geog, 1000)
                ) s1 ON true
                LEFT JOIN LATERAL (
                    SELECT COUNT(*)::int as cnt FROM pois
                    WHERE category = 'school' AND ST_DWithin(geog, n.center_geog, 3000)
                ) s3 ON true
                LEFT JOIN LATERAL (
                    SELECT
                        MIN(ST_Distance(p.geog, n.center_geog) / 1000.0) as nearest_km,
                        COUNT(*) FILTER (WHERE ST_Distance(p.geog, n.center_geog) <= 3000)::int as top_3km
                    FROM pois p
                    WHERE p.category = 'school'
                      AND (p.tags->>'rank')::int <= 25
                      AND ST_DWithin(p.geog, n.center_geog, 5000)
                ) ranked ON true
                LEFT JOIN LATERAL (
                    SELECT COUNT(DISTINCT split_part(p.tags->>'board', '/', 1))::int as board_count
                    FROM pois p
                    WHERE p.category = 'school' AND ST_DWithin(p.geog, n.center_geog, 5000)
                      AND p.tags->>'board' IS NOT NULL
                ) boards ON true
                WHERE n.center_geog IS NOT NULL
            """)
            school_map: dict[int, float] = {}
            for sr in school_rows:
                if sr["within_1km"] > 0:
                    rte = 100
                elif sr["within_3km"] > 0:
                    rte = 60
                else:
                    rte = 20
                if sr["ranked_km"] is not None:
                    top_prox = _decay(float(sr["ranked_km"]), 1.0, 5.0)
                    bonus = min(int(sr["top_3km"]) * 0.1, 0.3)
                    quality = min(top_prox + bonus, 1.0) * 100
                else:
                    quality = 0
                diversity = min(int(sr["board_count"]) / 4.0, 1.0) * 100
                school_map[sr["id"]] = round(
                    0.30 * rte + 0.25 * quality + 0.15 * diversity + 0.15 * 50 + 0.15 * 50, 1
                )

            # ── Future infrastructure: station proximity + diversity + construction ──
            infra_rows = await conn.fetch("""
                SELECT n.id,
                       s.name as station_name, p.name as project_name,
                       p.status, p.expected_completion,
                       ST_Distance(s.geog, n.center_geog) as distance_m
                FROM neighborhoods n
                JOIN future_infra_stations s ON ST_DWithin(s.geog, n.center_geog, 5000)
                JOIN future_infra_projects p ON s.project_id = p.id
                WHERE n.center_geog IS NOT NULL
                ORDER BY n.id, ST_Distance(s.geog, n.center_geog)
            """)
            infra_map: dict[int, float] = {}
            current_id = None
            stations_data: list[tuple] = []
            for ir in infra_rows:
                nid = ir["id"]
                if nid != current_id:
                    if current_id is not None:
                        infra_map[current_id] = _compute_infra_score(stations_data)
                    current_id = nid
                    stations_data = []
                stations_data.append((
                    float(ir["distance_m"]),
                    ir["project_name"],
                    ir["status"],
                    ir["expected_completion"],
                ))
            if current_id is not None:
                infra_map[current_id] = _compute_infra_score(stations_data)

            # ── Cleanliness: slum density + waste infrastructure ──
            clean_rows = await conn.fetch("""
                SELECT n.id,
                       COALESCE(slum.cnt, 0) as slum_count,
                       COALESCE(slum.avg_dn, 0) as slum_avg_dn,
                       COALESCE(dw.nearest_m, 99999) as waste_nearest_m,
                       COALESCE(dw.cnt_5km, 0) as waste_count_5km,
                       COALESCE(lf.nearest_m, 99999) as landfill_nearest_m,
                       COALESCE(pr.nearest_m, 99999) as processing_nearest_m
                FROM neighborhoods n
                LEFT JOIN LATERAL (
                    SELECT COUNT(*)::int as cnt, AVG(deprivation_dn)::float as avg_dn
                    FROM slum_zones WHERE ST_DWithin(centroid_geog, n.center_geog, 2000)
                ) slum ON true
                LEFT JOIN LATERAL (
                    SELECT MIN(ST_Distance(w.geog, n.center_geog))::float as nearest_m,
                           COUNT(*) FILTER (WHERE ST_DWithin(w.geog, n.center_geog, 5000))::int as cnt_5km
                    FROM waste_infrastructure w WHERE w.type = 'dry_waste_centre'
                ) dw ON true
                LEFT JOIN LATERAL (
                    SELECT MIN(ST_Distance(w.geog, n.center_geog))::float as nearest_m
                    FROM waste_infrastructure w WHERE w.type = 'landfill'
                ) lf ON true
                LEFT JOIN LATERAL (
                    SELECT MIN(ST_Distance(w.geog, n.center_geog))::float as nearest_m
                    FROM waste_infrastructure w WHERE w.type IN ('waste_processing', 'biomethanisation')
                ) pr ON true
                WHERE n.center_geog IS NOT NULL
            """)
            clean_map: dict[int, float] = {}
            for cr in clean_rows:
                s1 = _slum_density_score(int(cr["slum_count"]), float(cr["slum_avg_dn"]))
                s2 = _waste_access_score(float(cr["waste_nearest_m"]), int(cr["waste_count_5km"]))
                s3 = _landfill_penalty_score(float(cr["landfill_nearest_m"]))
                s4 = _processing_score(float(cr["processing_nearest_m"]))
                clean_map[cr["id"]] = round(min(100, max(0, 0.40 * s1 + 0.30 * s2 + 0.15 * s3 + 0.15 * s4)), 1)

            # ── Builder reputation: avg score of builders active in area ──
            all_builders = await conn.fetch(
                "SELECT name, active_areas, score FROM builders ORDER BY score DESC"
            )
            builder_top10_avg = 50.0
            if all_builders:
                builder_top10_avg = sum(float(b["score"]) for b in all_builders[:10]) / min(len(all_builders), 10)

        # ── Assemble final scores ──
        # Pre-compute builder area map
        builder_area_scores: dict[str, list[float]] = {}
        for b in all_builders:
            areas_raw = b["active_areas"]
            if not areas_raw:
                continue
            import json as _json
            if isinstance(areas_raw, str):
                try:
                    areas_list = _json.loads(areas_raw)
                except (ValueError, _json.JSONDecodeError):
                    areas_list = [a.strip() for a in areas_raw.split(",")]
            else:
                areas_list = areas_raw
            for area in areas_list:
                key = area.strip().lower()
                if key:
                    builder_area_scores.setdefault(key, []).append(float(b["score"]))

        neighborhoods = []
        for r in base_rows:
            nid = r["id"]
            name_lower = r["name"].lower()

            builder_scores = builder_area_scores.get(name_lower, [])
            builder_val = sum(builder_scores) / len(builder_scores) if builder_scores else builder_top10_avg

            dim_scores = {
                "safety": float(r["safety_score"] or 50),
                "walkability": float(r["walkability_score"] or 50),
                "water_supply": float(r["water_score"] or 50),
                "power_reliability": float(r["power_score"] or 50),
                "flood_risk": float(r["flood_score"] or 50),
                "affordability": float(r["affordability_score"] or 50),
                "noise": float(r["noise_score"] or 50),
                "business_opportunity": float(r["business_score"] or 50),
                "delivery_coverage": float(r["delivery_score"] or 50),
                "commute": float(r["commute_score"] if r["commute_score"] is not None else 50),
                "transit_access": transit_map.get(nid, 50),
                "hospital_access": hospital_map.get(nid, 50),
                "school_access": school_map.get(nid, 50),
                "air_quality": aqi_map.get(nid, 50),
                "future_infrastructure": infra_map.get(nid, 20),
                "cleanliness": clean_map.get(nid, 50),
                "builder_reputation": round(builder_val, 1),
            }

            composite = round(sum(
                SCORE_WEIGHTS.get(key, 0) * dim_scores.get(key, 50)
                for key in SCORE_WEIGHTS
            ), 1)

            price_sqft = int(r["avg_price_sqft"]) if r["avg_price_sqft"] else None
            growth = round(float(r["yoy_growth_pct"]), 1) if r["yoy_growth_pct"] else None

            neighborhoods.append({
                "name": r["name"],
                "latitude": float(r["lat"]),
                "longitude": float(r["lon"]),
                "score": composite,
                "label": score_label(composite),
                "avg_price_sqft": price_sqft,
                "yoy_growth_pct": growth,
            })

        # Deduplicate: when two neighborhoods are within 500m, keep the higher-scored one
        from math import radians, sin, cos, sqrt, atan2
        def _hav(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
            dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
            a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
            return 6371000 * 2 * atan2(sqrt(a), sqrt(1 - a))

        neighborhoods.sort(key=lambda n: n["score"], reverse=True)
        deduped: list[dict] = []
        for n in neighborhoods:
            too_close = False
            for kept in deduped:
                if _hav(n["latitude"], n["longitude"], kept["latitude"], kept["longitude"]) < 500:
                    too_close = True
                    break
            if not too_close:
                deduped.append(n)

        _prefetch_cache = {"neighborhoods": deduped}
        return _prefetch_cache

    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Prefetch failed: {e}")
        return {"neighborhoods": []}


def _compute_infra_score(stations: list[tuple]) -> float:
    """Compute future infra score from list of (distance_m, project_name, status, expected)."""
    def completion_weight(expected: str | None) -> float:
        if not expected:
            return 0.3
        try:
            year = int(str(expected).split("-")[0])
        except (ValueError, IndexError):
            return 0.3
        if year <= 2026: return 1.0
        if year <= 2027: return 0.85
        if year <= 2028: return 0.7
        if year <= 2029: return 0.55
        return 0.4

    def tod_decay(d_m: float) -> float:
        if d_m <= 500: return 1.0
        if d_m <= 800: return 1.0 - 0.5 * (d_m - 500) / 300
        if d_m <= 3000: return 0.5 - 0.5 * (d_m - 800) / 2200
        return 0.0

    proximity = 0.0
    project_names = set()
    has_construction = False
    count = 0
    for dist_m, proj_name, status, expected in stations:
        if dist_m <= 3000:
            project_names.add(proj_name)
        if status and "construction" in str(status).lower() and dist_m <= 2000:
            has_construction = True
        if dist_m <= 2000 and count < 5:
            proximity += tod_decay(dist_m) * completion_weight(expected) * 20
            count += 1

    proximity = min(proximity, 60)
    diversity = min(len(project_names) * 8, 25)
    construction_bonus = 15 if has_construction else 0
    return round(min(proximity + diversity + construction_bonus, 100), 1)


def _slum_density_score(count: int, avg_dn: float) -> float:
    if count == 0:
        return 100.0
    severity = min(avg_dn / 245.0, 1.0)
    penalty = count * (0.5 + 0.5 * severity)
    return max(0.0, min(100.0, 100.0 - penalty * 2.0))


def _waste_access_score(nearest_m: float, count_5km: int) -> float:
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
    density_bonus = min(count_5km * 2, 20)
    return min(100.0, base + density_bonus)


def _landfill_penalty_score(nearest_m: float) -> float:
    if nearest_m < 1000: return 0.0
    if nearest_m < 2000: return 25.0 * (nearest_m - 1000) / 1000
    if nearest_m < 3000: return 25.0 + 25.0 * (nearest_m - 2000) / 1000
    if nearest_m < 5000: return 50.0 + 25.0 * (nearest_m - 3000) / 2000
    return 100.0


def _processing_score(nearest_m: float) -> float:
    if nearest_m <= 2000: return 100.0
    if nearest_m <= 5000: return 100.0 - 50.0 * (nearest_m - 2000) / 3000
    if nearest_m <= 10000: return 50.0 - 25.0 * (nearest_m - 5000) / 5000
    return 25.0


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "neighbourhood-score"}


@router.get("/config/map")
async def map_config():
    from app.config import GOOGLE_MAPS_API_KEY, GOOGLE_MAPS_MAP_ID, BANGALORE_CENTER
    return {
        "google_maps_api_key": GOOGLE_MAPS_API_KEY,
        "google_maps_map_id": GOOGLE_MAPS_MAP_ID,
        "center": {"lat": BANGALORE_CENTER[0], "lon": BANGALORE_CENTER[1]},
    }


@router.post("/commute/refresh")
async def refresh_commute(input: LocationInput):
    """Live Google Maps Distance Matrix call for a specific location."""
    import json
    import urllib.request
    import urllib.parse
    import datetime
    from app.config import GOOGLE_MAPS_API_KEY

    lat, lon = None, None
    if input.latitude is not None and input.longitude is not None:
        lat, lon = input.latitude, input.longitude
    elif input.address:
        result = geocode_address(input.address)
        if result:
            lat, lon = result

    if not lat or not lon or not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=400, detail="Location or API key missing")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Find nearest neighborhood
        neighborhood = await conn.fetchrow(
            "SELECT id, name FROM neighborhoods ORDER BY ST_Distance(center_geog, ST_Point($1, $2)::geography) LIMIT 1",
            lon, lat,
        )
        if not neighborhood:
            raise HTTPException(status_code=404, detail="No neighborhood found")

        # Get all tech parks
        tech_parks = await conn.fetch("SELECT id, name, ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon FROM tech_parks")

    tp_coords = "|".join(f"{tp['lat']},{tp['lon']}" for tp in tech_parks)

    # Call Google Maps Distance Matrix API with traffic
    now = datetime.datetime.now(datetime.timezone.utc)
    days_ahead = (0 - now.weekday()) % 7 or 7
    next_monday = now + datetime.timedelta(days=days_ahead)
    peak_ts = int(next_monday.replace(hour=3, minute=30, second=0).timestamp())

    params = urllib.parse.urlencode({
        "origins": f"{lat},{lon}",
        "destinations": tp_coords,
        "mode": "driving",
        "departure_time": str(peak_ts),
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_API_KEY,
    })
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json?{params}"

    try:
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Google API error: {e}")

    if data["status"] != "OK":
        raise HTTPException(status_code=502, detail=f"Google API: {data['status']}")

    # Update DB with fresh data
    results = []
    async with pool.acquire() as conn:
        for j, tp in enumerate(tech_parks):
            elem = data["rows"][0]["elements"][j]
            if elem["status"] != "OK":
                continue
            no_traffic = elem["duration"]["value"] / 60.0
            peak = elem["duration_in_traffic"]["value"] / 60.0 if "duration_in_traffic" in elem else no_traffic
            dist_km = elem["distance"]["value"] / 1000.0

            for mode, dur in [("car_no_traffic", no_traffic), ("car_peak", peak)]:
                await conn.execute(
                    """INSERT INTO commute_times (neighborhood_id, tech_park_id, mode, duration_min, distance_km, route_summary)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT (neighborhood_id, tech_park_id, mode) DO UPDATE SET
                         duration_min = EXCLUDED.duration_min, distance_km = EXCLUDED.distance_km""",
                    neighborhood["id"], tp["id"], mode, round(dur, 1), round(dist_km, 1),
                    f"Live Google Maps ({mode.replace('_', ' ')}) to {tp['name']}",
                )

            results.append({
                "tech_park": tp["name"],
                "no_traffic_min": round(no_traffic, 1),
                "peak_min": round(peak, 1),
                "distance_km": round(dist_km, 1),
                "traffic_multiplier": round(peak / no_traffic, 1) if no_traffic > 0 else 1.0,
            })

    return {
        "neighborhood": neighborhood["name"],
        "refreshed": len(results),
        "source": "Google Maps Distance Matrix API (live)",
        "commutes": sorted(results, key=lambda x: x["peak_min"]),
    }


@router.post("/transit/walk")
async def live_transit_walk(input: LocationInput):
    """Live Google Maps Directions walking time to nearest transit stations."""
    import json
    import urllib.request
    import urllib.parse
    from app.config import GOOGLE_MAPS_API_KEY

    lat, lon = None, None
    if input.latitude is not None and input.longitude is not None:
        lat, lon = input.latitude, input.longitude
    elif input.address:
        result = geocode_address(input.address)
        if result:
            lat, lon = result

    if not lat or not lon or not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=400, detail="Location or API key missing")

    pool = await get_pool()
    results = []

    async with pool.acquire() as conn:
        for transit_type, table in [("metro", "metro_stations"), ("bus", "bus_stops"), ("train", "train_stations")]:
            row = await conn.fetchrow(
                f"""SELECT name, ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon,
                           ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as straight_km
                    FROM {table}
                    ORDER BY geog <-> ST_Point($1, $2)::geography LIMIT 1""",
                lon, lat,
            )
            if not row:
                continue

            # Google Directions walking API
            params = urllib.parse.urlencode({
                "origin": f"{lat},{lon}",
                "destination": f"{row['lat']},{row['lon']}",
                "mode": "walking",
                "key": GOOGLE_MAPS_API_KEY,
            })
            url = f"https://maps.googleapis.com/maps/api/directions/json?{params}"

            walk_km, walk_min = round(float(row["straight_km"]) * 1.4, 2), None
            try:
                resp = urllib.request.urlopen(url, timeout=10)
                data = json.loads(resp.read().decode("utf-8"))
                if data["status"] == "OK" and data["routes"]:
                    leg = data["routes"][0]["legs"][0]
                    walk_km = round(leg["distance"]["value"] / 1000.0, 2)
                    walk_min = round(leg["duration"]["value"] / 60.0, 1)
            except Exception:
                pass

            if walk_min is None:
                walk_min = round(walk_km / 5.0 * 60, 1)

            results.append({
                "type": transit_type,
                "name": row["name"],
                "straight_line_km": round(float(row["straight_km"]), 2),
                "walk_km": walk_km,
                "walk_minutes": walk_min,
                "source": "Google Maps Directions API (walking)",
            })

    return {"results": results}


_KEY_TRANSIT_HUBS = [
    ("Kempegowda International Airport", 13.1989, 77.7068),
    ("Kempegowda Bus Station (Majestic)", 12.9770, 77.5720),
    ("Bangalore City Railway Station (SBC)", 12.9767, 77.5690),
]


async def collect_locality_data(pool, lat: float, lon: float) -> dict:
    """Collect all available neighborhood data for a location from DB + cache.

    Used to give Claude real, ground-truth context when verifying claims.
    Mirrors verify_ai._collect_neighborhood_data but async and geography-based.
    """
    import asyncio
    from app.lib.commute_verifier import get_commute_data

    data: dict = {"latitude": lat, "longitude": lon}

    async with pool.acquire() as conn:
        # Nearest neighborhood
        nb = await conn.fetchrow(
            """SELECT id, name, ST_Distance(center_geog, ST_Point($1,$2)::geography)/1000.0 AS dist_km
               FROM neighborhoods
               WHERE ST_DWithin(center_geog, ST_Point($1,$2)::geography, 5000)
               ORDER BY center_geog <-> ST_Point($1,$2)::geography LIMIT 1""",
            lon, lat,
        )
        if nb:
            data["neighborhood"] = {"name": nb["name"], "distance_km": round(nb["dist_km"], 2)}
            nid = nb["id"]
        else:
            nid = None

        # Safety zone (proximity-based)
        sz = await conn.fetchrow(
            """SELECT zone_name, crime_rate_per_100k, streetlight_pct, cctv_density_per_sqkm,
                      police_density_per_sqkm, score
               FROM safety_zones
               WHERE center_geog IS NOT NULL
                 AND ST_DWithin(center_geog, ST_Point($1,$2)::geography, 3000)
               ORDER BY center_geog <-> ST_Point($1,$2)::geography
               LIMIT 1""",
            lon, lat,
        )
        if not sz and nid:
            sz = await conn.fetchrow(
                "SELECT zone_name, crime_rate_per_100k, streetlight_pct, cctv_density_per_sqkm, police_density_per_sqkm, score FROM safety_zones WHERE neighborhood_id=$1", nid,
            )
        if sz:
            data["safety"] = dict(sz)

        # Property prices
        pp = await conn.fetchrow(
            """SELECT area, avg_price_sqft, price_range_low, price_range_high,
                      avg_2bhk_lakh, avg_3bhk_lakh, avg_2bhk_rent, avg_3bhk_rent,
                      yoy_growth_pct, rental_yield_pct, affordability_score, affordability_label
               FROM property_prices
               WHERE center_geog IS NOT NULL
                 AND ST_DWithin(center_geog, ST_Point($1,$2)::geography, 3000)
               ORDER BY center_geog <-> ST_Point($1,$2)::geography
               LIMIT 1""",
            lon, lat,
        )
        if not pp and nid:
            pp = await conn.fetchrow(
                """SELECT area, avg_price_sqft, price_range_low, price_range_high,
                          avg_2bhk_lakh, avg_3bhk_lakh, avg_2bhk_rent, avg_3bhk_rent,
                          yoy_growth_pct, rental_yield_pct, affordability_score, affordability_label
                   FROM property_prices WHERE neighborhood_id=$1""", nid,
            )
        if pp:
            from decimal import Decimal as _Decimal
            data["property_prices"] = {k: (float(v) if isinstance(v, _Decimal) else v) for k, v in dict(pp).items()}

        # Water zone
        wz = await conn.fetchrow(
            "SELECT area, stage, supply_hours, reliability, score FROM water_zones WHERE neighborhood_id=$1", nid,
        ) if nid else None
        if wz:
            data["water_supply"] = dict(wz)

        # Power zone
        pz = await conn.fetchrow(
            "SELECT area, tier, avg_monthly_outage_hours, score FROM power_zones WHERE neighborhood_id=$1", nid,
        ) if nid else None
        if pz:
            data["power_supply"] = dict(pz)

        # Walkability
        wk = await conn.fetchrow(
            "SELECT area, score FROM walkability_zones WHERE neighborhood_id=$1", nid,
        ) if nid else None
        if wk:
            data["walkability"] = dict(wk)

        # Nearest metro
        metro = await conn.fetchrow(
            """SELECT m.name, m.status, ST_Distance(m.geog, ST_Point($1,$2)::geography)/1000.0 AS dist_km
               FROM metro_stations m
               WHERE ST_DWithin(m.geog, ST_Point($1,$2)::geography, 10000)
               ORDER BY m.geog <-> ST_Point($1,$2)::geography LIMIT 1""",
            lon, lat,
        )
        if metro:
            data["nearest_metro"] = {"name": metro["name"], "status": metro["status"], "distance_km": round(metro["dist_km"], 2)}

        # Flood risk
        if nid:
            fl = await conn.fetchrow(
                "SELECT risk_level, flood_history_events, drainage_quality, score FROM flood_risk WHERE neighborhood_id=$1", nid,
            )
            if fl:
                data["flood_risk"] = dict(fl)

        # Commute to top tech parks
        if nid:
            ct_rows = await conn.fetch(
                """SELECT tp.name, ct.duration_min, ct.distance_km
                   FROM commute_times ct JOIN tech_parks tp ON ct.tech_park_id=tp.id
                   WHERE ct.neighborhood_id=$1 AND ct.mode='car_peak'
                   ORDER BY ct.duration_min LIMIT 3""", nid,
            )
            if ct_rows:
                data["commute_to_tech_parks"] = [
                    {"tech_park": r["name"], "peak_min": round(float(r["duration_min"])), "km": round(float(r["distance_km"]), 1)}
                    for r in ct_rows
                ]

        # Delivery coverage
        if nid:
            dc = await conn.fetchrow(
                """SELECT swiggy_serviceable, zepto_serviceable, blinkit_serviceable,
                          bigbasket_serviceable, coverage_score
                   FROM delivery_coverage WHERE neighborhood_id=$1""", nid,
            )
            if dc:
                services = []
                if dc["swiggy_serviceable"]: services.append("Swiggy")
                if dc["zepto_serviceable"]: services.append("Zepto")
                if dc["blinkit_serviceable"]: services.append("Blinkit")
                if dc["bigbasket_serviceable"]: services.append("BigBasket")
                data["delivery_coverage"] = {"services": services, "count": len(services), "score": dc["coverage_score"]}

        # Noise
        if nid:
            nz = await conn.fetchrow(
                """SELECT avg_noise_db_estimate, noise_label, airport_flight_path,
                          highway_proximity_km, score
                   FROM noise_zones WHERE neighborhood_id=$1""", nid,
            )
            if nz:
                data["noise"] = {
                    "db": round(float(nz["avg_noise_db_estimate"])) if nz["avg_noise_db_estimate"] else None,
                    "label": nz["noise_label"],
                    "airport_flight_path": nz["airport_flight_path"],
                    "highway_km": round(float(nz["highway_proximity_km"]), 1) if nz["highway_proximity_km"] else None,
                    "score": nz["score"],
                }

        # Nearby top schools (5km)
        schools = await conn.fetch(
            """SELECT name, board, rank, area, fee_range_lakh_pa, seats, admission_difficulty,
                      ST_Distance(geog, ST_Point($1,$2)::geography)/1000.0 AS distance_km
               FROM schools
               WHERE ST_DWithin(geog, ST_Point($1,$2)::geography, 5000)
               ORDER BY geog <-> ST_Point($1,$2)::geography LIMIT 5""",
            lon, lat,
        )
        if schools:
            data["nearby_schools"] = [
                {k: (round(float(v), 2) if k == "distance_km" else v) for k, v in dict(s).items()}
                for s in schools
            ]

        # Nearby NABH hospitals (5km)
        hospitals = await conn.fetch(
            """SELECT name, accreditation, tier, specialties, beds, area,
                      ST_Distance(geog, ST_Point($1,$2)::geography)/1000.0 AS distance_km
               FROM hospitals
               WHERE ST_DWithin(geog, ST_Point($1,$2)::geography, 5000)
               ORDER BY geog <-> ST_Point($1,$2)::geography LIMIT 5""",
            lon, lat,
        )
        if hospitals:
            data["nearby_hospitals"] = [
                {k: (round(float(v), 2) if k == "distance_km" else v) for k, v in dict(s).items()}
                for s in hospitals
            ]

    # Precomputed composite scores
    cached_score = _find_cached_score(lat, lon)
    if cached_score:
        dims = {}
        for key in ("walkability", "safety", "transit_access", "hospital", "school",
                     "air_quality", "water_supply", "power", "future_infra",
                     "property_price", "flood_risk", "commute", "delivery_coverage",
                     "noise", "business_opportunity", "cleanliness"):
            if key in cached_score and isinstance(cached_score[key], dict):
                dims[key] = {
                    "score": cached_score[key].get("score"),
                    "label": cached_score[key].get("label"),
                }
        data["composite_score"] = cached_score.get("composite_score")
        data["composite_label"] = cached_score.get("composite_label")
        data["dimension_scores"] = dims

    # Key transit hub distances (airport, Majestic, railway station) via Google Maps
    hub_tasks = [
        get_commute_data(pool, lat, lon, h_lat, h_lon, h_name, "driving")
        for h_name, h_lat, h_lon in _KEY_TRANSIT_HUBS
    ]
    hub_results = await asyncio.gather(*hub_tasks, return_exceptions=True)
    key_distances = {}
    for (h_name, _, _), result in zip(_KEY_TRANSIT_HUBS, hub_results):
        if isinstance(result, Exception):
            continue
        key_distances[h_name] = {
            "peak_minutes": round(result["peak_duration_seconds"] / 60),
            "offpeak_minutes": round(result["offpeak_duration_seconds"] / 60),
            "road_km": round(result["distance_meters"] / 1000, 1),
            "source": result["source"],
        }
    if key_distances:
        data["key_distances"] = key_distances

    return data


@router.post("/verify-claims", response_model=ClaimVerificationResponse)
async def verify_claims(input: ClaimInput):
    """Verify property ad claims against real data using Claude + landmark registry."""
    from app.lib.claim_parser import parse_claims, split_claims_text, generate_claim_narrative, verify_claims_via_ai
    from app.lib.landmark_resolver import resolve_destination
    from app.lib.commute_verifier import get_commute_data, compute_verdict, haversine_meters

    lat, lon = None, None
    if input.latitude is not None and input.longitude is not None:
        lat, lon = input.latitude, input.longitude
    elif input.address:
        result = geocode_address(input.address)
        if result is None:
            raise HTTPException(status_code=400, detail=f"Could not geocode: '{input.address}'")
        lat, lon = result
    else:
        raise HTTPException(status_code=400, detail="Provide latitude/longitude or address.")

    address = reverse_geocode(lat, lon)
    pool = await get_pool()

    # Collect locality data for AI enrichment (runs in parallel with claim splitting)
    locality_data = await collect_locality_data(pool, lat, lon)

    # If raw_text is provided, use AI to split into atomic claims
    claims = input.claims
    if input.raw_text and input.raw_text.strip():
        try:
            split_result = await split_claims_text(input.raw_text)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        claims = split_result if split_result else claims
    elif not claims:
        raise HTTPException(status_code=400, detail="Provide claims or raw_text to verify.")

    # Parse all claims via Claude (or regex fallback)
    parsed_claims = await parse_claims(claims)

    verifications: list[ClaimVerification] = []

    for i, claim in enumerate(claims):
        parsed = parsed_claims[i] if i < len(parsed_claims) else {}
        destination = parsed.get("destination")
        claimed_value = parsed.get("claimed_value")
        claimed_unit = parsed.get("claimed_unit")
        travel_mode = parsed.get("travel_mode", "unspecified")
        dest_type = parsed.get("destination_type", "generic")
        is_proximity = parsed.get("is_proximity_claim", False)

        # Resolve destination to coordinates
        resolved = await resolve_destination(
            pool, destination, dest_type, origin_lat=lat, origin_lon=lon,
        ) if destination else None

        if not resolved:
            verifications.append(ClaimVerification(
                original_claim=claim,
                claimed_value=str(claimed_value) + f" {claimed_unit}" if claimed_value else "—",
                actual_value="—",
                difference="—",
                verdict="UNRESOLVED",
                details={
                    "parsed_destination": destination,
                    "note": f"Could not resolve '{destination}' to a known location.",
                    "_needs_ai_verify": True,
                },
            ))
            continue

        # For proximity claims without specific values, compute distance
        if is_proximity or claimed_value is None:
            crow_m = haversine_meters(lat, lon, resolved["latitude"], resolved["longitude"])
            crow_km = crow_m / 1000
            road_km = crow_km * 1.4

            if crow_km <= 1.0:
                verdict = "ACCURATE"
                explanation = f"{resolved['name']} is {round(crow_km, 1)} km away (straight line) — genuinely nearby."
            elif crow_km <= 3.0:
                verdict = "SLIGHTLY_MISLEADING"
                explanation = f"{resolved['name']} is {round(crow_km, 1)} km away ({round(road_km, 1)} km by road) — relatively close but not 'nearby'."
            else:
                verdict = "MISLEADING"
                explanation = f"{resolved['name']} is {round(crow_km, 1)} km away ({round(road_km, 1)} km by road) — not close."

            verifications.append(ClaimVerification(
                original_claim=claim,
                claimed_value="nearby" if is_proximity else "—",
                actual_value=f"{round(road_km, 1)} km by road / {round(crow_km, 1)} km straight",
                difference=f"{round(road_km, 1)} km",
                verdict=verdict,
                details={
                    "destination": resolved["name"],
                    "destination_category": resolved["category"],
                    "straight_line_km": round(crow_km, 2),
                    "road_estimate_km": round(road_km, 2),
                    "resolution_method": resolved["resolution_method"],
                    "explanation": explanation,
                    "destination_lat": resolved["latitude"],
                    "destination_lng": resolved["longitude"],
                },
            ))
            continue

        # For specific claims (X min, X km), get commute data and verify
        gm_mode = "walking" if travel_mode == "walk" else "driving"
        commute = await get_commute_data(
            pool, lat, lon,
            resolved["latitude"], resolved["longitude"],
            resolved["name"], gm_mode,
        )

        verdict_data = compute_verdict(
            claimed_value, claimed_unit,
            commute["peak_duration_seconds"],
            commute["distance_meters"],
            commute["crow_fly_distance_meters"],
            travel_mode,
        )

        if claimed_unit in ("min", "minutes"):
            actual_min = commute["peak_duration_seconds"] / 60
            offpeak_min = commute["offpeak_duration_seconds"] / 60
            actual_formatted = f"{round(actual_min)} min (peak)" + (f" / {round(offpeak_min)} min (off-peak)" if abs(actual_min - offpeak_min) > 2 else "")
            delta = round(actual_min - claimed_value, 1)
            diff_str = f"+{round(delta)} min" if delta > 0 else ("accurate" if abs(delta) < 2 else f"{round(delta)} min")
        else:
            road_km = commute["distance_meters"] / 1000
            crow_km = commute["crow_fly_distance_meters"] / 1000
            actual_formatted = f"{round(road_km, 1)} km (road) / {round(crow_km, 1)} km (straight)"
            delta = round(road_km - claimed_value, 1)
            diff_str = f"+{round(delta, 1)} km" if delta > 0 else "accurate"

        verifications.append(ClaimVerification(
            original_claim=claim,
            claimed_value=f"{claimed_value} {claimed_unit}",
            actual_value=actual_formatted,
            difference=diff_str,
            verdict=verdict_data["verdict"],
            details={
                "destination": resolved["name"],
                "destination_category": resolved["category"],
                "resolution_method": resolved["resolution_method"],
                "peak_duration_min": round(commute["peak_duration_seconds"] / 60, 1),
                "offpeak_duration_min": round(commute["offpeak_duration_seconds"] / 60, 1),
                "road_distance_km": round(commute["distance_meters"] / 1000, 2),
                "straight_line_km": round(commute["crow_fly_distance_meters"] / 1000, 2),
                "ratio": verdict_data["ratio"],
                "reality_gap_multiplier": verdict_data["reality_gap_multiplier"],
                "explanation": verdict_data["explanation"],
                "data_source": commute["source"],
                "destination_lat": resolved["latitude"],
                "destination_lng": resolved["longitude"],
            },
        ))

    # AI fallback for unresolved claims
    unresolved_indices = [
        i for i, v in enumerate(verifications)
        if v.verdict == "UNRESOLVED" and v.details.get("_needs_ai_verify")
    ]
    if unresolved_indices:
        unresolved_texts = [verifications[i].original_claim for i in unresolved_indices]
        ai_results = await verify_claims_via_ai(address, lat, lon, unresolved_texts, locality_data=locality_data)
        for idx, ai_result in zip(unresolved_indices, ai_results):
            if isinstance(ai_result, dict) and ai_result.get("verdict"):
                verifications[idx] = ClaimVerification(
                    original_claim=verifications[idx].original_claim,
                    claimed_value=ai_result.get("claimed_value", "—"),
                    actual_value=ai_result.get("actual_value", "—"),
                    difference="—",
                    verdict=ai_result["verdict"],
                    details={
                        "explanation": ai_result.get("explanation", ""),
                        "data_source": "ai_verification",
                    },
                )

    # Build summary
    misleading = sum(1 for v in verifications if v.verdict in ("MISLEADING", "SIGNIFICANTLY_MISLEADING"))
    slight = sum(1 for v in verifications if v.verdict == "SLIGHTLY_MISLEADING")
    accurate = sum(1 for v in verifications if v.verdict == "ACCURATE")
    unresolved = sum(1 for v in verifications if v.verdict in ("UNRESOLVED", "UNVERIFIABLE"))
    total = len(verifications)

    if misleading > 0:
        summary = f"{misleading} of {total} claims are misleading — verify carefully before deciding"
    elif slight > 0:
        summary = f"{slight} of {total} claims are slightly optimistic — common in real estate ads"
    elif unresolved > 0:
        summary = f"{accurate} of {total} claims verified as accurate, {unresolved} could not be verified"
    else:
        summary = f"All {total} claims are accurate — this listing's claims check out"

    # Generate AI narrative analysis
    verification_dicts = [
        {
            "original_claim": v.original_claim,
            "claimed_value": v.claimed_value,
            "actual_value": v.actual_value,
            "difference": v.difference,
            "verdict": v.verdict,
            "details": v.details,
        }
        for v in verifications
    ]
    property_label = input.address or address
    narrative = await generate_claim_narrative(property_label, verification_dicts, summary, locality_data=locality_data)

    return ClaimVerificationResponse(
        latitude=lat, longitude=lon, address=address,
        results=verifications, summary=summary,
        narrative=narrative,
        extracted_claims=claims,
    )


@router.get("/data-freshness")
async def data_freshness():
    """Return data freshness metadata from the data_freshness table."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT table_name, source_name, last_seeded_at, last_refreshed_at, record_count, status FROM data_freshness"
            )
        result = {}
        for r in rows:
            result[r["table_name"]] = {
                "source": r["source_name"],
                "last_seeded": r["last_seeded_at"].isoformat() if r["last_seeded_at"] else None,
                "last_refreshed": r["last_refreshed_at"].isoformat() if r["last_refreshed_at"] else None,
                "record_count": r["record_count"],
                "status": r["status"],
            }
        return result
    except Exception:
        return {}
