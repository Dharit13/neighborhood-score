"""
Resolve destination names to coordinates using the landmark_registry.

Resolution order:
  1. Exact name match in landmark_registry
  2. Alias match in landmark_registry
  3. Fuzzy ILIKE match in landmark_registry
  4. Category-based nearest match (e.g., "metro" -> nearest metro_station)
  5. Google Places API fallback
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


async def resolve_destination(
    pool,
    destination: str,
    destination_type: str = "generic",
    origin_lat: float = None,
    origin_lon: float = None,
) -> Optional[dict]:
    """
    Resolve a destination name to coordinates.

    Returns dict with: name, latitude, longitude, category, resolution_method
    Or None if unresolvable.
    """
    if not destination:
        return None

    dest_lower = destination.lower().strip()

    async with pool.acquire() as conn:
        # 1. Exact name match
        row = await conn.fetchrow(
            """SELECT name, latitude, longitude, category
               FROM landmark_registry
               WHERE LOWER(name) = $1
               LIMIT 1""",
            dest_lower,
        )
        if row:
            return _to_result(row, "exact_match")

        # 2. Alias match
        row = await conn.fetchrow(
            """SELECT name, latitude, longitude, category
               FROM landmark_registry
               WHERE EXISTS (
                   SELECT 1 FROM unnest(aliases) a
                   WHERE LOWER(a) = $1
               )
               LIMIT 1""",
            dest_lower,
        )
        if row:
            return _to_result(row, "alias_match")

        # 3. Fuzzy ILIKE match (destination in name, or name in destination)
        row = await conn.fetchrow(
            """SELECT name, latitude, longitude, category
               FROM landmark_registry
               WHERE LOWER(name) LIKE '%' || $1 || '%'
                  OR $1 LIKE '%' || LOWER(name) || '%'
               ORDER BY LENGTH(name) DESC
               LIMIT 1""",
            dest_lower,
        )
        if row:
            return _to_result(row, "fuzzy_match")

        # 3b. Fuzzy match against aliases
        row = await conn.fetchrow(
            """SELECT name, latitude, longitude, category
               FROM landmark_registry
               WHERE EXISTS (
                   SELECT 1 FROM unnest(aliases) a
                   WHERE LOWER(a) LIKE '%' || $1 || '%'
                      OR $1 LIKE '%' || LOWER(a) || '%'
               )
               ORDER BY LENGTH(name) DESC
               LIMIT 1""",
            dest_lower,
        )
        if row:
            return _to_result(row, "alias_fuzzy_match")

        # 4. Category-based nearest (for generic "metro", "school", etc.)
        if destination_type != "generic" and origin_lat and origin_lon:
            category_map = {
                "metro_station": "metro_station",
                "tech_park": "tech_park",
                "airport": "airport",
                "hospital": "hospital",
                "school": "school",
                "mall": "mall",
                "railway_station": "railway_station",
                "bus_terminal": "bus_terminal",
                "junction": "junction",
            }
            cat = category_map.get(destination_type)
            if cat:
                row = await conn.fetchrow(
                    """SELECT name, latitude, longitude, category
                       FROM landmark_registry
                       WHERE category = $1
                       ORDER BY geog <-> ST_Point($2, $3)::geography
                       LIMIT 1""",
                    cat, origin_lon, origin_lat,
                )
                if row:
                    return _to_result(row, "nearest_by_category")

        # 4b. Line-based metro resolution (e.g., "Purple Line Metro Station", "Blue Line")
        metro_line_keywords = {
            "purple": "purple",
            "green": "green",
            "yellow": "yellow",
            "blue": "blue",
            "pink": "pink",
            "orange": "orange",
        }
        for keyword, line_name in metro_line_keywords.items():
            if keyword in dest_lower and ("line" in dest_lower or "metro" in dest_lower):
                if origin_lat and origin_lon:
                    row = await conn.fetchrow(
                        """SELECT name, ST_Y(geog::geometry) as latitude,
                                  ST_X(geog::geometry) as longitude,
                                  ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as dist_km
                           FROM metro_stations
                           WHERE LOWER(line) LIKE '%' || $3 || '%'
                           ORDER BY geog <-> ST_Point($1, $2)::geography
                           LIMIT 1""",
                        origin_lon, origin_lat, line_name,
                    )
                    if row:
                        return {
                            "name": f"{row['name']} ({line_name.title()} Line)",
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"]),
                            "category": "metro_station",
                            "resolution_method": f"nearest_{line_name}_line_metro",
                        }
                    # Also check landmark_registry for upcoming lines
                    row = await conn.fetchrow(
                        """SELECT name, latitude, longitude, category
                           FROM landmark_registry
                           WHERE category = 'metro_station'
                             AND (LOWER(line) LIKE '%' || $3 || '%' OR LOWER(name) LIKE '%' || $3 || '%')
                           ORDER BY geog <-> ST_Point($1, $2)::geography
                           LIMIT 1""",
                        origin_lon, origin_lat, line_name,
                    )
                    if row:
                        return _to_result(row, f"nearest_{line_name}_line_landmark")
                break

        # 4c. Generic "metro" or "bus stop" resolution
        if dest_lower in ("metro", "metro station", "nearest metro", "nearest metro station"):
            if origin_lat and origin_lon:
                row = await conn.fetchrow(
                    """SELECT name, ST_Y(geog::geometry) as latitude,
                              ST_X(geog::geometry) as longitude
                       FROM metro_stations
                       ORDER BY geog <-> ST_Point($1, $2)::geography
                       LIMIT 1""",
                    origin_lon, origin_lat,
                )
                if row:
                    return {
                        "name": row["name"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "category": "metro_station",
                        "resolution_method": "nearest_metro_from_db",
                    }

        if dest_lower in ("bus stop", "bus station", "nearest bus stop"):
            if origin_lat and origin_lon:
                row = await conn.fetchrow(
                    """SELECT name, ST_Y(geog::geometry) as latitude,
                              ST_X(geog::geometry) as longitude
                       FROM bus_stops
                       ORDER BY geog <-> ST_Point($1, $2)::geography
                       LIMIT 1""",
                    origin_lon, origin_lat,
                )
                if row:
                    return {
                        "name": row["name"],
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "category": "bus_stop",
                        "resolution_method": "nearest_bus_from_db",
                    }

        # 5. Fall back to legacy tables (union of metro, tech_parks, hospitals, schools)
        row = await conn.fetchrow(
            """SELECT name, ST_Y(geog::geometry) as latitude,
                      ST_X(geog::geometry) as longitude, 'legacy' as category
               FROM (
                   SELECT name, geog FROM metro_stations UNION ALL
                   SELECT name, geog FROM tech_parks UNION ALL
                   SELECT name, geog FROM hospitals UNION ALL
                   SELECT name, geog FROM schools
               ) combined
               WHERE LOWER(name) LIKE '%' || $1 || '%'
               ORDER BY ST_Distance(geog, ST_Point($2, $3)::geography)
               LIMIT 1""",
            dest_lower, origin_lon or 77.59, origin_lat or 12.97,
        )
        if row:
            return {
                "name": row["name"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "category": row["category"],
                "resolution_method": "legacy_table_match",
            }

    # 6. Google Places API fallback
    return await _google_places_resolve(destination, origin_lat, origin_lon)


async def _google_places_resolve(
    destination: str, origin_lat: float = None, origin_lon: float = None
) -> Optional[dict]:
    """Last resort: use Google Places text search."""
    if not GOOGLE_MAPS_API_KEY:
        return None

    try:
        import httpx
        query = f"{destination}, Bangalore" if "bangalore" not in destination.lower() else destination
        params = {
            "query": query,
            "key": GOOGLE_MAPS_API_KEY,
        }
        if origin_lat and origin_lon:
            params["location"] = f"{origin_lat},{origin_lon}"
            params["radius"] = "30000"

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results"):
                    place = data["results"][0]
                    loc = place["geometry"]["location"]
                    return {
                        "name": place.get("name", destination),
                        "latitude": loc["lat"],
                        "longitude": loc["lng"],
                        "category": "google_places",
                        "resolution_method": "google_places_api",
                    }
    except Exception as e:
        logger.debug(f"Google Places resolve failed: {e}")

    return None


def _to_result(row, method: str) -> dict:
    return {
        "name": row["name"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "category": row["category"],
        "resolution_method": method,
    }
