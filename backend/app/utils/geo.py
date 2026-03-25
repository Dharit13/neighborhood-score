import math
import os
import httpx
import logging

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

CROW_FLY_CORRECTION = 1.4


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def walk_minutes(distance_km: float, speed_kmh: float = 5.0) -> float:
    return (distance_km / speed_kmh) * 60


def decay_score(distance_km: float, full_score_km: float = 0.5, zero_score_km: float = 2.0) -> float:
    """Linear decay: full points at <= full_score_km, zero at >= zero_score_km."""
    if distance_km <= full_score_km:
        return 1.0
    if distance_km >= zero_score_km:
        return 0.0
    return 1.0 - (distance_km - full_score_km) / (zero_score_km - full_score_km)


def _lookup_neighborhood_coords(address: str) -> tuple[float, float] | None:
    """Check our neighborhoods DB first — instant, free, and uses our curated coordinates."""
    try:
        from app.db import get_sync_conn
        conn = get_sync_conn()
        try:
            with conn.cursor() as cur:
                addr_lower = address.lower().replace(", bangalore", "").replace(", bengaluru", "").replace(", karnataka, india", "").strip()
                # Exact name match
                cur.execute(
                    """SELECT ST_Y(center_geog::geometry), ST_X(center_geog::geometry)
                       FROM neighborhoods WHERE LOWER(name) = %s LIMIT 1""",
                    (addr_lower,),
                )
                row = cur.fetchone()
                if row:
                    return (row[0], row[1])
                # Partial match — neighborhood name appears in the address
                cur.execute(
                    """SELECT ST_Y(center_geog::geometry), ST_X(center_geog::geometry), name
                       FROM neighborhoods WHERE %s LIKE '%%' || LOWER(name) || '%%'
                       ORDER BY LENGTH(name) DESC LIMIT 1""",
                    (addr_lower,),
                )
                row = cur.fetchone()
                if row:
                    return (row[0], row[1])
                # Alias match — check if address appears in any neighborhood's aliases
                cur.execute(
                    """SELECT ST_Y(center_geog::geometry), ST_X(center_geog::geometry)
                       FROM neighborhoods
                       WHERE EXISTS (SELECT 1 FROM unnest(aliases) a WHERE LOWER(a) = %s)
                       LIMIT 1""",
                    (addr_lower,),
                )
                row = cur.fetchone()
                if row:
                    return (row[0], row[1])
        finally:
            conn.close()
    except Exception as e:
        logger.debug(f"DB neighborhood lookup failed: {e}")
    return None


def geocode_address(address: str) -> tuple[float, float] | None:
    """Look up neighborhood from DB first, fall back to Google Maps Geocoding API."""
    db_result = _lookup_neighborhood_coords(address)
    if db_result:
        return db_result

    if "bangalore" not in address.lower() and "bengaluru" not in address.lower():
        address = f"{address}, Bangalore, Karnataka, India"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"address": address, "key": GOOGLE_MAPS_API_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    loc = data["results"][0]["geometry"]["location"]
                    return (loc["lat"], loc["lng"])
    except Exception as e:
        logger.warning(f"Google geocode failed: {e}")
    return None


def reverse_geocode(lat: float, lon: float) -> str:
    """Reverse geocode using Google Maps API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={"latlng": f"{lat},{lon}", "key": GOOGLE_MAPS_API_KEY},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    return data["results"][0]["formatted_address"]
    except Exception as e:
        logger.warning(f"Google reverse geocode failed: {e}")
    return f"{lat:.4f}, {lon:.4f}"


def find_nearest(lat: float, lon: float, points: list[dict], top_n: int = 5) -> list[dict]:
    """Find nearest points from a list of dicts with 'latitude' and 'longitude' keys."""
    results = []
    for p in points:
        dist = haversine_km(lat, lon, p["latitude"], p["longitude"])
        results.append({**p, "distance_km": round(dist, 3)})
    results.sort(key=lambda x: x["distance_km"])
    return results[:top_n]


def count_within_radius(lat: float, lon: float, points: list[dict], radius_km: float) -> int:
    count = 0
    for p in points:
        if haversine_km(lat, lon, p["latitude"], p["longitude"]) <= radius_km:
            count += 1
    return count


def _google_walk_time(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float] | None:
    """Google Maps Directions walking time. More accurate than ORS for Indian cities."""
    if not GOOGLE_MAPS_API_KEY:
        return None
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": f"{lat1},{lon1}",
                    "destination": f"{lat2},{lon2}",
                    "mode": "walking",
                    "key": GOOGLE_MAPS_API_KEY,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("routes"):
                    leg = data["routes"][0]["legs"][0]
                    dist_km = round(leg["distance"]["value"] / 1000, 2)
                    time_min = round(leg["duration"]["value"] / 60, 1)
                    return dist_km, time_min
    except Exception as e:
        logger.debug(f"Google Directions walking failed: {e}")
    return None


def actual_walk_time(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float]:
    """
    Get actual pedestrian walking distance (km) and time (minutes).
    Tries Google Maps Directions first (more accurate for Indian cities),
    falls back to OpenRouteService, then to haversine * correction factor.
    """
    google_result = _google_walk_time(lat1, lon1, lat2, lon2)
    if google_result:
        return google_result

    try:
        url = "https://api.openrouteservice.org/v2/directions/foot-walking"
        params = {
            "start": f"{lon1},{lat1}",
            "end": f"{lon2},{lat2}",
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                segment = data["features"][0]["properties"]["segments"][0]
                dist_km = round(segment["distance"] / 1000, 2)
                time_min = round(segment["duration"] / 60, 1)
                return dist_km, time_min
    except Exception as e:
        logger.debug(f"OpenRouteService failed: {e}")

    straight = haversine_km(lat1, lon1, lat2, lon2)
    corrected_km = round(straight * CROW_FLY_CORRECTION, 2)
    corrected_min = round(walk_minutes(corrected_km), 1)
    return corrected_km, corrected_min


def marketing_walk_claim(straight_line_km: float) -> float:
    """What a real-estate marketing team would claim as walk time (straight-line / fast speed)."""
    return round((straight_line_km / 6.0) * 60, 1)


def drive_time_estimate(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float, float]:
    """
    Estimate driving distance and time via OpenRouteService driving profile.
    Returns (drive_distance_km, offpeak_minutes, peak_minutes).
    Peak applies a 2.0x Bangalore traffic multiplier.
    Falls back to haversine-based estimate if API fails.
    """
    BANGALORE_PEAK_FACTOR = 2.0

    try:
        url = "https://api.openrouteservice.org/v2/directions/driving-car"
        params = {
            "start": f"{lon1},{lat1}",
            "end": f"{lon2},{lat2}",
        }
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                segment = data["features"][0]["properties"]["segments"][0]
                dist_km = round(segment["distance"] / 1000, 2)
                offpeak_min = round(segment["duration"] / 60, 1)
                peak_min = round(offpeak_min * BANGALORE_PEAK_FACTOR, 1)
                return dist_km, offpeak_min, peak_min
    except Exception as e:
        logger.debug(f"OpenRouteService driving failed: {e}")

    straight = haversine_km(lat1, lon1, lat2, lon2)
    road_km = round(straight * CROW_FLY_CORRECTION, 2)
    offpeak = round((road_km / 25.0) * 60, 1)
    peak = round(offpeak * BANGALORE_PEAK_FACTOR, 1)
    return road_km, offpeak, peak
