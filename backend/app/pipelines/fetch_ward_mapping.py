"""
Fetch GBA 2025 ward boundaries and map them to our neighborhoods.

Source: GBA Wards Delimitation 2025 — data.opencity.in (Public Domain, Dec 2025)
        369 wards across 5 corporations (Central, South, East, West, North)
        Includes ward polygons, names (English + Kannada), population (2011 census)

For each of our 74 neighborhoods, finds all wards whose centroid falls within
the neighborhood's radius, creating a ward-to-neighborhood mapping.
"""

import math
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.db import get_sync_conn

GBA_WARDS_KML_URL = (
    "https://data.opencity.in/dataset/863209cb-4ced-4f51-b5c5-156939c50922/"
    "resource/9013d656-8051-4e2d-9648-46efd0d86d3d/download/"
    "gba-369-wards-december-2025.kml"
)

KML_NS = "http://www.opengis.net/kml/2.2"


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _parse_wards_kml(content: str) -> list[dict]:
    """Parse ward placemarks from GBA KML."""
    wards = []
    root = ET.fromstring(content)

    for pm in root.iter(f"{{{KML_NS}}}Placemark"):
        ward_name = None
        ward_name_kn = None
        corporation = None
        population = None

        for sd in pm.findall(f".//{{{KML_NS}}}SimpleData"):
            attr = sd.get("name")
            if attr == "ward_name" and sd.text:
                ward_name = sd.text.strip()
            elif attr == "ward_name_kn" and sd.text:
                ward_name_kn = sd.text.strip()
            elif attr == "Corporation" and sd.text:
                corporation = sd.text.strip()
            elif attr == "TOT_P" and sd.text:
                try:
                    population = int(float(sd.text))
                except ValueError:
                    pass

        if not ward_name:
            continue

        coords_elem = pm.find(f".//{{{KML_NS}}}coordinates")
        if coords_elem is None or not coords_elem.text:
            continue

        raw = coords_elem.text.strip().split()
        parsed = []
        for c in raw:
            parts = c.split(",")
            if len(parts) >= 2:
                try:
                    parsed.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue

        if len(parsed) < 3:
            continue

        lons = [p[0] for p in parsed]
        lats = [p[1] for p in parsed]
        centroid_lat = sum(lats) / len(lats)
        centroid_lon = sum(lons) / len(lons)

        wards.append(
            {
                "name": ward_name,
                "name_kn": ward_name_kn,
                "corporation": corporation or "Unknown",
                "population": population,
                "lat": centroid_lat,
                "lon": centroid_lon,
            }
        )

    return wards


def fetch():
    print("  Downloading GBA 369 Wards KML (data.opencity.in, Dec 2025)...")
    try:
        req = urllib.request.Request(GBA_WARDS_KML_URL, headers={"User-Agent": "bangalore-score/1.0"})
        resp = urllib.request.urlopen(req, timeout=60)
        kml_content = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR: Could not download wards KML: {e}")
        return 0

    wards = _parse_wards_kml(kml_content)
    print(f"  Parsed {len(wards)} wards with coordinates")

    if not wards:
        print("  WARNING: No wards parsed")
        return 0

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, ST_Y(center_geog::geometry) as lat, ST_X(center_geog::geometry) as lon, radius_km FROM neighborhoods"
            )
            neighborhoods = cur.fetchall()

            cur.execute("DELETE FROM ward_mapping")
            count = 0

            for nid, nname, nlat, nlon, nradius in neighborhoods:
                for w in wards:
                    dist = _haversine_km(nlat, nlon, w["lat"], w["lon"])
                    if dist <= max(nradius or 2.0, 5.0):
                        cur.execute(
                            """INSERT INTO ward_mapping
                               (neighborhood_id, ward_name, ward_name_kn, corporation, population, centroid_geog, distance_km)
                               VALUES (%s, %s, %s, %s, %s, ST_Point(%s, %s)::geography, %s)""",
                            (
                                nid,
                                w["name"],
                                w["name_kn"],
                                w["corporation"],
                                w["population"],
                                w["lon"],
                                w["lat"],
                                round(dist, 2),
                            ),
                        )
                        count += 1

        conn.commit()
        print(f"  OK: {count} ward-to-neighborhood mappings created across {len(neighborhoods)} neighborhoods")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
