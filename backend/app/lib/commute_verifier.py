"""
Commute verification engine.

Given an origin (property location) and a resolved destination,
compute the actual commute time/distance and compare against
the builder's claim.

Uses:
  - commute_cache table for cached results
  - Google Maps Distance Matrix API for live lookups
  - Haversine for crow-fly distance
"""

import os
import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _round_coord(val: float, decimals: int = 4) -> float:
    """Round to 4 decimal places (~11m precision) for cache keys."""
    return round(val, decimals)


async def get_commute_data(
    pool,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    dest_name: str,
    travel_mode: str = "driving",
) -> dict:
    """
    Get commute data between two points.

    Returns dict with:
      peak_duration_seconds, offpeak_duration_seconds,
      distance_meters, crow_fly_distance_meters,
      source (cache|google_api|estimate)
    """
    o_lat = _round_coord(origin_lat)
    o_lng = _round_coord(origin_lon)
    d_lat = _round_coord(dest_lat)
    d_lng = _round_coord(dest_lon)

    crow_fly_m = haversine_meters(origin_lat, origin_lon, dest_lat, dest_lon)

    # Check cache first
    async with pool.acquire() as conn:
        cached = await conn.fetchrow(
            """SELECT peak_duration_seconds, offpeak_duration_seconds,
                      distance_meters, crow_fly_distance_meters
               FROM commute_cache
               WHERE origin_lat = $1 AND origin_lng = $2
                 AND destination_lat = $3 AND destination_lng = $4
                 AND travel_mode = $5
                 AND expires_at > now()""",
            o_lat, o_lng, d_lat, d_lng, travel_mode,
        )

        if cached:
            return {
                "peak_duration_seconds": cached["peak_duration_seconds"],
                "offpeak_duration_seconds": cached["offpeak_duration_seconds"],
                "distance_meters": cached["distance_meters"],
                "crow_fly_distance_meters": cached["crow_fly_distance_meters"] or int(crow_fly_m),
                "source": "cache",
            }

    # Google Maps Distance Matrix API
    if GOOGLE_MAPS_API_KEY and travel_mode in ("driving", "walk", "walking"):
        gm_mode = "walking" if travel_mode in ("walk", "walking") else "driving"
        result = await _google_distance_matrix(
            origin_lat, origin_lon, dest_lat, dest_lon, gm_mode
        )
        if result:
            result["crow_fly_distance_meters"] = int(crow_fly_m)
            result["source"] = "google_api"

            # Cache the result
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO commute_cache
                       (origin_lat, origin_lng, destination_lat, destination_lng,
                        destination_name, travel_mode,
                        peak_duration_seconds, offpeak_duration_seconds,
                        distance_meters, crow_fly_distance_meters)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                       ON CONFLICT (origin_lat, origin_lng, destination_lat, destination_lng, travel_mode)
                       DO UPDATE SET
                         peak_duration_seconds = EXCLUDED.peak_duration_seconds,
                         offpeak_duration_seconds = EXCLUDED.offpeak_duration_seconds,
                         distance_meters = EXCLUDED.distance_meters,
                         crow_fly_distance_meters = EXCLUDED.crow_fly_distance_meters,
                         queried_at = now(),
                         expires_at = now() + interval '7 days'""",
                    o_lat, o_lng, d_lat, d_lng, dest_name, travel_mode,
                    result["peak_duration_seconds"],
                    result["offpeak_duration_seconds"],
                    result["distance_meters"],
                    int(crow_fly_m),
                )

            return result

    # Fallback: haversine-based estimate
    road_distance_m = crow_fly_m * 1.4
    if travel_mode in ("walk", "walking"):
        speed_ms = 5.0 / 3.6  # 5 km/h
        duration_s = int(road_distance_m / speed_ms)
        return {
            "peak_duration_seconds": duration_s,
            "offpeak_duration_seconds": duration_s,
            "distance_meters": int(road_distance_m),
            "crow_fly_distance_meters": int(crow_fly_m),
            "source": "estimate",
        }
    else:
        offpeak_speed_ms = 25.0 / 3.6  # 25 km/h
        offpeak_s = int(road_distance_m / offpeak_speed_ms)
        peak_s = int(offpeak_s * 2.0)  # Bangalore peak factor
        return {
            "peak_duration_seconds": peak_s,
            "offpeak_duration_seconds": offpeak_s,
            "distance_meters": int(road_distance_m),
            "crow_fly_distance_meters": int(crow_fly_m),
            "source": "estimate",
        }


async def _google_distance_matrix(
    lat1: float, lon1: float, lat2: float, lon2: float, mode: str
) -> Optional[dict]:
    """Call Google Maps Distance Matrix API with peak traffic modeling."""
    try:
        import httpx

        params = {
            "origins": f"{lat1},{lon1}",
            "destinations": f"{lat2},{lon2}",
            "mode": mode,
            "key": GOOGLE_MAPS_API_KEY,
        }

        if mode == "driving":
            # Monday 8:30 AM IST = Sunday 27:00 UTC... approximate next Monday
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0 and now.hour >= 3:
                days_until_monday = 7
            next_monday = now + datetime.timedelta(days=days_until_monday)
            peak_time = next_monday.replace(hour=3, minute=0, second=0, microsecond=0)  # 8:30 AM IST = 3:00 UTC
            params["departure_time"] = str(int(peak_time.timestamp()))
            params["traffic_model"] = "pessimistic"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params=params,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            if data.get("status") != "OK":
                return None

            element = data["rows"][0]["elements"][0]
            if element.get("status") != "OK":
                return None

            distance_m = element["distance"]["value"]

            if mode == "driving" and "duration_in_traffic" in element:
                peak_s = element["duration_in_traffic"]["value"]
                offpeak_s = element["duration"]["value"]
            else:
                duration_s = element["duration"]["value"]
                peak_s = duration_s
                offpeak_s = duration_s

            return {
                "peak_duration_seconds": peak_s,
                "offpeak_duration_seconds": offpeak_s,
                "distance_meters": distance_m,
            }

    except Exception as e:
        logger.debug(f"Google Distance Matrix failed: {e}")
        return None


def compute_verdict(
    claimed_value: float,
    claimed_unit: str,
    actual_peak_seconds: int,
    actual_distance_meters: int,
    crow_fly_meters: int,
    travel_mode: str,
) -> dict:
    """
    Compare claimed vs actual and produce a verdict.

    Returns dict with: verdict, ratio, explanation, reality_gap_multiplier
    """
    if claimed_unit in ("min", "minutes"):
        actual_min = actual_peak_seconds / 60
        ratio = actual_min / claimed_value if claimed_value > 0 else 1

        if ratio <= 1.2:
            verdict = "ACCURATE"
            explanation = f"Actual peak time is ~{round(actual_min)} min, consistent with the claim of {round(claimed_value)} min."
        elif ratio <= 1.8:
            verdict = "SLIGHTLY_MISLEADING"
            explanation = f"Actual peak time is ~{round(actual_min)} min vs claimed {round(claimed_value)} min — {round(ratio, 1)}x longer than advertised."
        elif ratio <= 3.0:
            verdict = "MISLEADING"
            explanation = f"Actual peak time is ~{round(actual_min)} min vs claimed {round(claimed_value)} min — {round(ratio, 1)}x longer. Significant understatement."
        else:
            verdict = "SIGNIFICANTLY_MISLEADING"
            explanation = f"Actual peak time is ~{round(actual_min)} min vs claimed {round(claimed_value)} min — {round(ratio, 1)}x longer. Grossly misleading."

        return {
            "verdict": verdict,
            "ratio": round(ratio, 2),
            "reality_gap_multiplier": round(ratio, 1),
            "explanation": explanation,
            "actual_value_formatted": f"{round(actual_min)} min (peak hour)",
            "actual_offpeak_formatted": None,
        }

    elif claimed_unit in ("km", "kilometers"):
        road_km = actual_distance_meters / 1000
        crow_km = crow_fly_meters / 1000
        ratio = road_km / claimed_value if claimed_value > 0 else 1

        if ratio <= 1.2:
            verdict = "ACCURATE"
            explanation = f"Road distance is {round(road_km, 1)} km (crow-fly {round(crow_km, 1)} km), consistent with claim of {claimed_value} km."
        elif ratio <= 1.8:
            verdict = "SLIGHTLY_MISLEADING"
            explanation = f"Road distance is {round(road_km, 1)} km vs claimed {claimed_value} km. Crow-fly is {round(crow_km, 1)} km — they may be using straight-line distance."
        elif ratio <= 3.0:
            verdict = "MISLEADING"
            explanation = f"Road distance is {round(road_km, 1)} km vs claimed {claimed_value} km — {round(ratio, 1)}x further by road."
        else:
            verdict = "SIGNIFICANTLY_MISLEADING"
            explanation = f"Road distance is {round(road_km, 1)} km vs claimed {claimed_value} km — {round(ratio, 1)}x further. Grossly misleading."

        return {
            "verdict": verdict,
            "ratio": round(ratio, 2),
            "reality_gap_multiplier": round(ratio, 1),
            "explanation": explanation,
            "actual_value_formatted": f"{round(road_km, 1)} km (road) / {round(crow_km, 1)} km (straight line)",
        }

    return {
        "verdict": "UNVERIFIABLE",
        "ratio": None,
        "reality_gap_multiplier": None,
        "explanation": "Could not verify — unsupported unit.",
        "actual_value_formatted": None,
    }
