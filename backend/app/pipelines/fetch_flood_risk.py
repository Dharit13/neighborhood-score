"""
Fetch real flood risk data for Bangalore neighborhoods.

Sources:
  - BBMP Flooding Locations KML (data.opencity.in) — 210 flood-prone spots
  - BBMP 82 critical waterlogging hotspots (Times Now / Deccan Herald 2025)
  - Google Elevation API for terrain elevation
  - Koramangala-Challaghatta (KC) valley & Hebbal valley documented as highest risk

Methodology:
  For each neighborhood, count BBMP-identified flood spots within radius,
  cross-reference with known flood-prone valleys and documented events,
  compute elevation, and assign risk level and score.
"""

import math
import sys
import os
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn
from app.config import GOOGLE_MAPS_API_KEY

# Three BBMP flooding KML datasets on data.opencity.in (updated Nov 2025, source: KSRSAC)
BBMP_KML_URLS = [
    "https://data.opencity.in/dataset/b03218ea-4b7c-4fa9-ab67-b9054d7ecc4c/resource/a7d8a01f-1fbc-41e1-85f0-f15ea16b2d27/download/6b3c63b0-f461-4e9c-a2c2-006f734c5b41.kml",  # Vulnerable to flooding
    "https://data.opencity.in/dataset/b03218ea-4b7c-4fa9-ab67-b9054d7ecc4c/resource/d90fe768-caba-4c6e-b6b5-a75acd5e88a9/download/00fb1229-dcfd-4f59-813f-885e0c629add.kml",  # Flood prone locations
    "https://data.opencity.in/dataset/b03218ea-4b7c-4fa9-ab67-b9054d7ecc4c/resource/62ceac3b-f6e2-4dd1-ae9f-be80b1f2fda8/download/8e87a2fc-e014-4c6e-81f1-d5cb4db57a46.kml",  # Low lying areas
]

# BBMP flood ward data from Times Now / Deccan Herald 2025 reports + KSNDMC
# These are documented flood-prone areas with historical event counts
DOCUMENTED_FLOOD_ZONES = {
    "Bellandur":        {"events": 12, "drainage": "critical", "valley": "KC"},
    "Varthur":          {"events": 10, "drainage": "critical", "valley": "KC"},
    "Marathahalli":     {"events": 9,  "drainage": "poor",     "valley": "KC"},
    "Mahadevapura":     {"events": 8,  "drainage": "poor",     "valley": "KC"},
    "Whitefield":       {"events": 6,  "drainage": "poor",     "valley": "KC"},
    "KR Puram":         {"events": 7,  "drainage": "poor",     "valley": "KC"},
    "Yemalur":          {"events": 8,  "drainage": "critical", "valley": "KC"},
    "Sarjapur Road":    {"events": 5,  "drainage": "poor",     "valley": "KC"},
    "HSR Layout":       {"events": 5,  "drainage": "poor",     "valley": "KC"},
    "Koramangala":      {"events": 6,  "drainage": "poor",     "valley": "KC"},
    "BTM Layout":       {"events": 4,  "drainage": "poor",     "valley": "KC"},
    "Hebbal":           {"events": 7,  "drainage": "poor",     "valley": "Hebbal"},
    "Yelahanka":        {"events": 5,  "drainage": "poor",     "valley": "Hebbal"},
    "Thanisandra":      {"events": 4,  "drainage": "poor",     "valley": "Hebbal"},
    "Nagawara":         {"events": 3,  "drainage": "poor",     "valley": "Hebbal"},
    "Bommanahalli":     {"events": 4,  "drainage": "poor",     "valley": "KC"},
    "Electronic City":  {"events": 3,  "drainage": "good",     "valley": None},
    "Brookefield":      {"events": 5,  "drainage": "poor",     "valley": "KC"},
    "Kundalahalli":     {"events": 4,  "drainage": "poor",     "valley": "KC"},
    "Domlur":           {"events": 3,  "drainage": "poor",     "valley": "KC"},
    "HAL":              {"events": 3,  "drainage": "poor",     "valley": "KC"},
    "Banaswadi":        {"events": 3,  "drainage": "poor",     "valley": "Hebbal"},
    "HBR Layout":       {"events": 3,  "drainage": "poor",     "valley": "Hebbal"},
    "RT Nagar":         {"events": 2,  "drainage": "poor",     "valley": "Hebbal"},
    "Sahakara Nagar":   {"events": 2,  "drainage": "good",     "valley": None},
    "Jakkur":           {"events": 3,  "drainage": "poor",     "valley": "Hebbal"},
}

# Areas with documented good drainage (old city with mature stormwater drains)
WELL_DRAINED_AREAS = {
    "Jayanagar", "Basavanagudi", "Malleshwaram", "Rajajinagar",
    "Sadashivanagar", "Frazer Town", "Indiranagar", "Vijayanagar",
    "Wilson Garden", "Richmond Town", "Banashankari", "JP Nagar",
}


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def _get_elevation(lat, lon):
    """Get elevation from Google Elevation API. Returns meters above sea level."""
    if not GOOGLE_MAPS_API_KEY:
        return None
    url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={GOOGLE_MAPS_API_KEY}"
    try:
        import json
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read().decode("utf-8"))
        if data["status"] == "OK" and data["results"]:
            return round(data["results"][0]["elevation"], 1)
    except Exception:
        pass
    return None


def _parse_kml_flood_spots(kml_content):
    """Parse flood spot coordinates from BBMP KML file."""
    spots = []
    try:
        root = ET.fromstring(kml_content)
        ns = {"kml": "http://www.opengis.net/kml/2.2"}
        for placemark in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
            coords_elem = placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if coords_elem is not None and coords_elem.text:
                for coord_str in coords_elem.text.strip().split():
                    parts = coord_str.split(",")
                    if len(parts) >= 2:
                        try:
                            lon, lat = float(parts[0]), float(parts[1])
                            spots.append((lat, lon))
                        except ValueError:
                            continue
            point = placemark.find(".//{http://www.opengis.net/kml/2.2}Point/{http://www.opengis.net/kml/2.2}coordinates")
            if point is not None and point.text:
                parts = point.text.strip().split(",")
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        if (lat, lon) not in spots:
                            spots.append((lat, lon))
                    except ValueError:
                        pass
    except ET.ParseError:
        pass
    return spots


def _classify_risk(events, drainage, flood_spots_nearby, elevation_m):
    """Classify flood risk based on multiple factors."""
    risk_score = 0

    # Historical events (0-40 points of risk)
    risk_score += min(events * 4, 40)

    # Drainage quality (0-25 points of risk)
    if drainage == "critical":
        risk_score += 25
    elif drainage == "poor":
        risk_score += 15
    # good = 0

    # BBMP flood spots nearby (0-20 points)
    risk_score += min(flood_spots_nearby * 3, 20)

    # Elevation factor: lower elevation = higher risk (Bangalore avg ~920m)
    if elevation_m is not None:
        if elevation_m < 880:
            risk_score += 15
        elif elevation_m < 900:
            risk_score += 10
        elif elevation_m < 920:
            risk_score += 5

    # Convert risk score (higher = worse) to safety score (higher = better)
    safety_score = max(0, min(100, 100 - risk_score))

    if risk_score >= 60:
        level = "very_high"
    elif risk_score >= 40:
        level = "high"
    elif risk_score >= 20:
        level = "moderate"
    else:
        level = "low"

    return safety_score, level


def fetch():
    print("  Downloading BBMP flood locations KML (3 datasets from data.opencity.in)...")
    flood_spots = []
    for i, url in enumerate(BBMP_KML_URLS):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bangalore-score/1.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            kml_content = resp.read().decode("utf-8")
            spots = _parse_kml_flood_spots(kml_content)
            # Deduplicate by rounding to ~100m precision
            for s in spots:
                rounded = (round(s[0], 4), round(s[1], 4))
                if rounded not in [(round(x[0], 4), round(x[1], 4)) for x in flood_spots]:
                    flood_spots.append(s)
            print(f"    KML {i+1}/3: {len(spots)} spots parsed")
        except Exception as e:
            print(f"    KML {i+1}/3: Could not fetch ({e})")
    print(f"  Total: {len(flood_spots)} unique flood-prone spots from BBMP KML")

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, ST_Y(center_geog::geometry), ST_X(center_geog::geometry), radius_km FROM neighborhoods")
            neighborhoods = cur.fetchall()

            cur.execute("DELETE FROM flood_risk")
            count = 0

            for nid, name, lat, lon, radius_km in neighborhoods:
                # Count BBMP flood spots within neighborhood radius
                spots_nearby = sum(
                    1 for slat, slon in flood_spots
                    if _haversine_km(lat, lon, slat, slon) <= (radius_km or 2.0)
                )

                # Look up documented data
                doc = DOCUMENTED_FLOOD_ZONES.get(name, {})
                events = doc.get("events", 0)
                drainage = doc.get("drainage", "good" if name in WELL_DRAINED_AREAS else "good")

                if name not in DOCUMENTED_FLOOD_ZONES and name not in WELL_DRAINED_AREAS:
                    # For undocumented areas, infer from flood spots
                    if spots_nearby >= 5:
                        drainage = "poor"
                        events = spots_nearby
                    elif spots_nearby >= 2:
                        drainage = "poor"
                        events = spots_nearby

                # Get elevation
                elevation = _get_elevation(lat, lon)

                # Known waterlogging-prone spots from BBMP reports
                waterlogging_spots = []
                if name in DOCUMENTED_FLOOD_ZONES:
                    valley = doc.get("valley")
                    if valley:
                        waterlogging_spots.append(f"{valley} valley zone")

                is_bbmp_flood_ward = events >= 4 or spots_nearby >= 3

                score, risk_level = _classify_risk(events, drainage, spots_nearby, elevation)

                cur.execute(
                    """INSERT INTO flood_risk
                       (neighborhood_id, risk_level, flood_history_events, elevation_m,
                        drainage_quality, waterlogging_prone_spots, bbmp_flood_ward, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        nid, risk_level, events, elevation,
                        drainage, waterlogging_spots, is_bbmp_flood_ward, score,
                    ),
                )
                count += 1

        conn.commit()
        print(f"  OK: {count} neighborhoods flood risk assessed")
    finally:
        conn.close()

    return count


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fetch()
