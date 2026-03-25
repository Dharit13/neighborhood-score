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
from app.config import SCORE_WEIGHTS

router = APIRouter(prefix="/api", tags=["scores"])


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
            try:
                narrative_obj = _json.loads(narrative_str)
                if isinstance(narrative_obj, dict):
                    verdict = narrative_obj.get("verdict", "")
                    pros = narrative_obj.get("pros", [])
                    cons = narrative_obj.get("cons", [])
                    best_for = narrative_obj.get("best_for", "")
                    avoid_if = narrative_obj.get("avoid_if", "")
                    narrative_str = verdict
            except (_json.JSONDecodeError, TypeError):
                pass

            return AIVerification(
                confidence=row["confidence"],
                narrative=narrative_str,
                verdict=verdict,
                pros=pros,
                cons=cons,
                best_for=best_for,
                avoid_if=avoid_if,
                flags=flags_raw,
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
    lat, lon = None, None

    user_provided_address = None
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


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "neighbourhood-score"}


@router.get("/config/map")
async def map_config():
    from app.config import GOOGLE_MAPS_API_KEY, BANGALORE_CENTER
    return {
        "google_maps_api_key": GOOGLE_MAPS_API_KEY,
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


@router.post("/verify-claims", response_model=ClaimVerificationResponse)
async def verify_claims(input: ClaimInput):
    """Verify property ad claims against real data."""
    import re

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

    verifications: list[ClaimVerification] = []

    for claim in input.claims:
        claim_lower = claim.lower().strip()

        # Pattern 1: transit walk claims — "X min from/to metro/station/bus"
        transit_match = re.search(r'(\d+)\s*min\w*\s*(?:from|to|walk\w*\s*(?:from|to)?)\s*(?:the\s+)?(?:nearest\s+)?(metro|bus\s*stop|train|railway|station)', claim_lower)
        if transit_match:
            claimed_min = int(transit_match.group(1))
            transit_type = transit_match.group(2).strip()

            table = "metro_stations"
            if "bus" in transit_type:
                table = "bus_stops"
            elif "train" in transit_type or "railway" in transit_type:
                table = "train_stations"

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"""SELECT name, ST_Y(geog::geometry) as lat, ST_X(geog::geometry) as lon,
                               ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as straight_km
                        FROM {table}
                        ORDER BY geog <-> ST_Point($1, $2)::geography LIMIT 1""",
                    lon, lat,
                )

            if row:
                actual_km, actual_min = actual_walk_time(lat, lon, row["lat"], row["lon"])
                delta = round(actual_min - claimed_min, 1)
                ratio = actual_min / claimed_min if claimed_min > 0 else 1

                if ratio <= 1.2:
                    verdict = "ACCURATE"
                elif ratio <= 1.5:
                    verdict = "SLIGHTLY_OPTIMISTIC"
                else:
                    verdict = "MISLEADING"

                verifications.append(ClaimVerification(
                    original_claim=claim,
                    claimed_value=f"{claimed_min} min",
                    actual_value=f"{round(actual_min)} min walk ({actual_km} km)",
                    difference=f"+{round(delta)} min" if delta > 0 else "accurate",
                    verdict=verdict,
                    details={
                        "nearest": row["name"],
                        "straight_line_km": round(float(row["straight_km"]), 2),
                        "actual_walk_km": actual_km,
                        "actual_walk_min": round(actual_min, 1),
                        "ratio": round(ratio, 2),
                    },
                ))
                continue

        # Pattern 2: commute/drive claims — "X min to [destination]"
        commute_match = re.search(r'(\d+)\s*min\w*\s*(?:from|to|drive\w*\s*(?:from|to)?)\s+(.+)', claim_lower)
        if commute_match:
            claimed_min = int(commute_match.group(1))
            destination = commute_match.group(2).strip().rstrip('.')

            async with pool.acquire() as conn:
                # Try matching against tech parks
                tp = await conn.fetchrow(
                    """SELECT tp.name, ST_Y(tp.geog::geometry) as lat, ST_X(tp.geog::geometry) as lon,
                              ct.duration_min as peak_min
                       FROM tech_parks tp
                       LEFT JOIN commute_times ct ON ct.tech_park_id = tp.id AND ct.mode = 'car_peak'
                       LEFT JOIN neighborhoods n ON ct.neighborhood_id = n.id
                       WHERE LOWER(tp.name) LIKE '%' || $3 || '%'
                       ORDER BY ST_Distance(n.center_geog, ST_Point($1, $2)::geography)
                       LIMIT 1""",
                    lon, lat, destination.replace("'", ""),
                )

            if tp and tp["peak_min"]:
                peak = float(tp["peak_min"])
                delta = round(peak - claimed_min, 1)
                ratio = peak / claimed_min if claimed_min > 0 else 1

                if ratio <= 1.2:
                    verdict = "ACCURATE"
                elif ratio <= 1.5:
                    verdict = "SLIGHTLY_OPTIMISTIC"
                else:
                    verdict = "MISLEADING"

                verifications.append(ClaimVerification(
                    original_claim=claim,
                    claimed_value=f"{claimed_min} min",
                    actual_value=f"{round(peak)} min (Mon 9 AM peak)",
                    difference=f"+{round(delta)} min" if delta > 0 else "accurate",
                    verdict=verdict,
                    details={
                        "destination": tp["name"],
                        "peak_traffic_min": round(peak, 1),
                        "ratio": round(ratio, 2),
                        "note": "Peak = Monday 9 AM via Google Distance Matrix",
                    },
                ))
                continue

            # Fallback: use haversine distance to give some answer
            straight_km = haversine_km(lat, lon, tp["lat"], tp["lon"]) if tp else None
            if straight_km:
                est_drive_min = round(straight_km / 25.0 * 60 * 2.0, 1)
                delta = round(est_drive_min - claimed_min, 1)
                ratio = est_drive_min / claimed_min if claimed_min > 0 else 1
                verdict = "ACCURATE" if ratio <= 1.2 else ("SLIGHTLY_OPTIMISTIC" if ratio <= 1.5 else "MISLEADING")
                verifications.append(ClaimVerification(
                    original_claim=claim,
                    claimed_value=f"{claimed_min} min",
                    actual_value=f"~{round(est_drive_min)} min (estimated peak)",
                    difference=f"+{round(delta)} min" if delta > 0 else "accurate",
                    verdict=verdict,
                    details={"destination": tp["name"], "straight_km": round(straight_km, 2), "note": "Estimated — no cached route data"},
                ))
                continue

        # Pattern 3: distance claims — "X km from [place]"
        dist_match = re.search(r'(\d+(?:\.\d+)?)\s*km\s*(?:from|to|near)\s+(.+)', claim_lower)
        if dist_match:
            claimed_km = float(dist_match.group(1))
            destination = dist_match.group(2).strip().rstrip('.')

            async with pool.acquire() as conn:
                place = await conn.fetchrow(
                    """SELECT name, ST_Y(geog::geometry) as plat, ST_X(geog::geometry) as plon
                       FROM (
                         SELECT name, geog FROM metro_stations UNION ALL
                         SELECT name, geog FROM tech_parks UNION ALL
                         SELECT name, geog FROM hospitals UNION ALL
                         SELECT name, geog FROM schools
                       ) combined
                       WHERE LOWER(name) LIKE '%' || $1 || '%'
                       ORDER BY ST_Distance(geog, ST_Point($2, $3)::geography)
                       LIMIT 1""",
                    destination.replace("'", ""), lon, lat,
                )

            if place:
                actual_km = round(haversine_km(lat, lon, place["plat"], place["plon"]), 2)
                road_km = round(actual_km * 1.4, 2)
                delta = round(road_km - claimed_km, 1)
                ratio = road_km / claimed_km if claimed_km > 0 else 1
                verdict = "ACCURATE" if ratio <= 1.2 else ("SLIGHTLY_OPTIMISTIC" if ratio <= 1.5 else "MISLEADING")
                verifications.append(ClaimVerification(
                    original_claim=claim,
                    claimed_value=f"{claimed_km} km",
                    actual_value=f"{road_km} km (road) / {actual_km} km (straight)",
                    difference=f"+{round(delta, 1)} km" if delta > 0 else "accurate",
                    verdict=verdict,
                    details={"destination": place["name"], "straight_line_km": actual_km, "road_estimate_km": road_km},
                ))
                continue

        # Unrecognized claim
        verifications.append(ClaimVerification(
            original_claim=claim,
            claimed_value="—",
            actual_value="—",
            difference="—",
            verdict="UNRECOGNIZED",
            details={"note": "Could not parse this claim. Try formats like '5 min from metro' or '20 min to Electronic City'."},
        ))

    misleading = sum(1 for v in verifications if v.verdict == "MISLEADING")
    optimistic = sum(1 for v in verifications if v.verdict == "SLIGHTLY_OPTIMISTIC")
    accurate = sum(1 for v in verifications if v.verdict == "ACCURATE")
    total = len(verifications)

    if misleading > 0:
        summary = f"{misleading} of {total} claims are misleading"
    elif optimistic > 0:
        summary = f"{optimistic} of {total} claims are slightly optimistic"
    else:
        summary = f"All {total} claims are accurate"

    return ClaimVerificationResponse(
        latitude=lat, longitude=lon, address=address,
        results=verifications, summary=summary,
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
