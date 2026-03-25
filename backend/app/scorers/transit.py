"""
Transit Access Score (0-100)

METHODOLOGY: MOHUA National Transit Oriented Development (TOD) Policy (2017)
Source: mohua.gov.in/upload/whatsnew/59a4070e85256Transit_Oriented_Developoment_Policy.pdf

Distance norms from TOD policy:
  - 500m = optimal walk catchment from transit station
  - 800m = acceptable walk catchment limit
  - Beyond 800m = requires feeder service, diminishing accessibility

Scoring uses linear decay between these policy thresholds:
  <= 500m: score 100
  500-800m: linear decay 100 -> 50
  800-2000m: linear decay 50 -> 0
  > 2000m: score 0

Modal weights reflect Indian urban transit hierarchy where metro provides
the highest capacity and reliability, followed by bus (BMTC), then rail.
"""

from app.db import get_pool
from app.utils.geo import actual_walk_time, marketing_walk_claim, drive_time_estimate, walk_minutes, haversine_km
from app.models import TransitScoreResult, TransitDetail, NearbyDetail, score_label

# MOHUA TOD Policy (2017) distance norms in meters
TOD_OPTIMAL_M = 500
TOD_ACCEPTABLE_M = 800
TOD_FEEDER_M = 2000

WALKABLE_THRESHOLD_KM = TOD_FEEDER_M / 1000.0

KIA_LAT, KIA_LON = 13.1979, 77.7063
MAJESTIC_BUS_LAT, MAJESTIC_BUS_LON = 12.9770, 77.5720
CITY_RAILWAY_LAT, CITY_RAILWAY_LON = 12.9783, 77.5694

SOURCES = [
    "MOHUA National TOD Policy (2017) — 500m optimal, 800m acceptable catchment",
    "BMTC Bus Stops — openbangalore GitHub",
    "Namma Metro Stations — data.opencity.in",
    "Indian Railways — South Western Railway zone",
    "Google Maps Directions API — pedestrian walking times (primary)",
    "OpenRouteService API — pedestrian routing (fallback)",
]


def _tod_proximity_score(distance_m: float) -> float:
    """Linear decay based on MOHUA TOD policy thresholds."""
    if distance_m <= TOD_OPTIMAL_M:
        return 100.0
    if distance_m <= TOD_ACCEPTABLE_M:
        return 100.0 - 50.0 * (distance_m - TOD_OPTIMAL_M) / (TOD_ACCEPTABLE_M - TOD_OPTIMAL_M)
    if distance_m <= TOD_FEEDER_M:
        return 50.0 - 50.0 * (distance_m - TOD_ACCEPTABLE_M) / (TOD_FEEDER_M - TOD_ACCEPTABLE_M)
    return 0.0


def _make_transit_detail(row: dict, transit_type: str, lat: float, lon: float) -> TransitDetail:
    straight_km = float(row["distance_km"])
    marketing_min = marketing_walk_claim(straight_km)

    if transit_type == "metro":
        name = f"{row['name']} ({(row.get('line') or 'metro').title()} Line)"
    elif transit_type == "train":
        name = f"{row['name']} ({(row.get('type') or 'railway').title()})"
    else:
        name = row["name"]

    if straight_km <= WALKABLE_THRESHOLD_KM:
        actual_km, actual_min = actual_walk_time(lat, lon, row["latitude"], row["longitude"])
        drive_km, offpeak, peak = None, None, None
        recommended = "walk"
    else:
        actual_km = round(straight_km * 1.4, 2)
        actual_min = round(walk_minutes(actual_km), 1)
        drive_km, offpeak, peak = drive_time_estimate(lat, lon, row["latitude"], row["longitude"])
        recommended = "drive/ride"

    return TransitDetail(
        name=name, type=transit_type,
        distance_km=straight_km, walk_minutes=actual_min,
        actual_walk_km=actual_km, marketing_claim_minutes=marketing_min,
        straight_line_km=straight_km, drive_km=drive_km,
        drive_offpeak_minutes=offpeak, drive_peak_minutes=peak,
        recommended_mode=recommended,
        latitude=row["latitude"], longitude=row["longitude"],
    )


def _make_fixed_poi_detail(
    name: str, poi_type: str,
    lat: float, lon: float, poi_lat: float, poi_lon: float,
) -> TransitDetail:
    """Build a TransitDetail for a well-known fixed location (airport, Majestic, SBC)."""
    straight_km = round(haversine_km(lat, lon, poi_lat, poi_lon), 1)
    drive_km, offpeak, peak = drive_time_estimate(lat, lon, poi_lat, poi_lon)
    return TransitDetail(
        name=name, type=poi_type,
        distance_km=straight_km,
        walk_minutes=round(walk_minutes(straight_km * 1.4), 1),
        straight_line_km=straight_km,
        drive_km=drive_km,
        drive_offpeak_minutes=offpeak,
        drive_peak_minutes=peak,
        recommended_mode="drive/ride",
        latitude=poi_lat, longitude=poi_lon,
    )


async def compute_transit_score(lat: float, lon: float) -> TransitScoreResult:
    pool = await get_pool()

    async with pool.acquire() as conn:
        nearest_metros = await conn.fetch(
            """SELECT name, line, status,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as distance_m,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM metro_stations
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 3""",
            lon, lat,
        )
        nearest_buses = await conn.fetch(
            """SELECT name, ward,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as distance_m,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM bus_stops
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 5""",
            lon, lat,
        )
        nearest_trains = await conn.fetch(
            """SELECT name, type,
                      ST_Y(geog::geometry) as latitude, ST_X(geog::geometry) as longitude,
                      ST_Distance(geog, ST_Point($1, $2)::geography) as distance_m,
                      ST_Distance(geog, ST_Point($1, $2)::geography) / 1000.0 as distance_km
               FROM train_stations
               ORDER BY geog <-> ST_Point($1, $2)::geography
               LIMIT 3""",
            lon, lat,
        )

    metro_m = float(nearest_metros[0]["distance_m"]) if nearest_metros else 99000
    bus_m = float(nearest_buses[0]["distance_m"]) if nearest_buses else 99000
    train_m = float(nearest_trains[0]["distance_m"]) if nearest_trains else 99000

    # TOD policy scoring for each mode
    metro_score = _tod_proximity_score(metro_m)
    bus_score = _tod_proximity_score(bus_m)
    train_score = _tod_proximity_score(train_m)

    # Multi-modal bonus: count modes within TOD acceptable zone (800m)
    modal_count = sum(1 for d in [metro_m, bus_m, train_m] if d <= TOD_ACCEPTABLE_M)
    multi_modal = min(modal_count / 3.0, 1.0) * 100

    # Metro-weighted composite (metro has highest capacity/reliability in Indian cities)
    final_score = round(min(max(
        0.35 * metro_score + 0.30 * bus_score + 0.20 * train_score + 0.15 * multi_modal,
        0), 100), 1)

    nearest_metro_detail = _make_transit_detail(nearest_metros[0], "metro", lat, lon) if nearest_metros else None
    nearest_bus_detail = _make_transit_detail(nearest_buses[0], "bus", lat, lon) if nearest_buses else None
    nearest_train_detail = _make_transit_detail(nearest_trains[0], "train", lat, lon) if nearest_trains else None

    peak_travel, offpeak_travel = None, None
    if nearest_metro_detail:
        if nearest_metro_detail.recommended_mode == "walk":
            reach = nearest_metro_detail.walk_minutes
        else:
            reach = nearest_metro_detail.drive_peak_minutes or nearest_metro_detail.walk_minutes
        peak_travel = round(reach + 5 + 15, 1)
        offpeak_travel = round((nearest_metro_detail.walk_minutes if nearest_metro_detail.recommended_mode == "walk"
                                else (nearest_metro_detail.drive_offpeak_minutes or nearest_metro_detail.walk_minutes)) + 3 + 12, 1)
    elif nearest_bus_detail and bus_m < TOD_FEEDER_M:
        peak_travel = round(nearest_bus_detail.walk_minutes + 10 + 35, 1)
        offpeak_travel = round(nearest_bus_detail.walk_minutes + 5 + 20, 1)

    details = []
    for m in nearest_metros[:2]:
        details.append(NearbyDetail(
            name=f"Metro: {m['name']} ({(m.get('line') or '').title()} Line)",
            distance_km=round(m["distance_km"], 2), category="metro",
            latitude=m["latitude"], longitude=m["longitude"],
        ))
    for b in nearest_buses[:3]:
        details.append(NearbyDetail(
            name=f"Bus: {b['name']}", distance_km=round(b["distance_km"], 2),
            category="bus_stop", latitude=b["latitude"], longitude=b["longitude"],
        ))
    for t in nearest_trains[:2]:
        details.append(NearbyDetail(
            name=f"Train: {t['name']} ({(t.get('type') or '')})",
            distance_km=round(t["distance_km"], 2), category="train_station",
            latitude=t["latitude"], longitude=t["longitude"],
        ))

    airport_detail = _make_fixed_poi_detail(
        "Kempegowda International Airport (KIA)", "airport",
        lat, lon, KIA_LAT, KIA_LON,
    )
    majestic_detail = _make_fixed_poi_detail(
        "Majestic Bus Station (Kempegowda)", "bus_station",
        lat, lon, MAJESTIC_BUS_LAT, MAJESTIC_BUS_LON,
    )
    city_railway_detail = _make_fixed_poi_detail(
        "KSR Bengaluru City Junction (SBC)", "railway_station",
        lat, lon, CITY_RAILWAY_LAT, CITY_RAILWAY_LON,
    )

    return TransitScoreResult(
        score=final_score, label=score_label(final_score), details=details,
        breakdown={
            "methodology": "MOHUA TOD Policy (2017) — 500m optimal, 800m acceptable",
            "metro_proximity": round(metro_score, 1),
            "bus_stop_proximity": round(bus_score, 1),
            "train_proximity": round(train_score, 1),
            "multi_modal_bonus": round(multi_modal, 1),
            "nearest_metro_m": round(metro_m, 0),
            "nearest_bus_m": round(bus_m, 0),
            "nearest_train_m": round(train_m, 0),
        },
        nearest_metro=nearest_metro_detail, nearest_bus_stop=nearest_bus_detail,
        nearest_train=nearest_train_detail,
        airport=airport_detail, majestic=majestic_detail,
        city_railway=city_railway_detail,
        peak_travel_time_min=peak_travel, offpeak_travel_time_min=offpeak_travel,
        sources=SOURCES,
    )
