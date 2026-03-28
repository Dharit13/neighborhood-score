"""
Fetch real police station locations from data.opencity.in (KSRSAC).

Sources:
  - Bengaluru Urban Police Station Locations KML (data.opencity.in, KSRSAC, Nov 2025)
  - Bengaluru Urban Police Outpost Locations KML (data.opencity.in, KSRSAC, Nov 2025)

Replaces the hardcoded 49-station JSON with real KSRSAC data.
"""

import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import BANGALORE_BBOX
from app.db import get_sync_conn

# Bengaluru Urban Police Stations (KSRSAC, updated Nov 2025)
PS_KML_URL = "https://data.opencity.in/dataset/1fe7e205-d00e-437e-b43d-6237f065dc2d/resource/b862cdc0-bf08-4706-9788-4f712d27f950/download/63a601fc-41a6-4e01-aad0-b053c67b392e.kml"
# Bengaluru Urban Police Outpost Locations (KSRSAC, updated Nov 2025)
OUTPOST_KML_URL = "https://data.opencity.in/dataset/1fe7e205-d00e-437e-b43d-6237f065dc2d/resource/59423322-eae5-4ee8-b7d5-db176d8077d8/download/74612016-6f67-4184-a160-6b3a8d3a012b.kml"

KML_NS = "{http://www.opengis.net/kml/2.2}"


def _parse_kml_stations(kml_content, station_type="station"):
    """Parse police station/outpost locations from KSRSAC KML.

    KSRSAC format uses ExtendedData/SchemaData with SimpleData fields
    (e.g. POL_STAName) and MultiGeometry/Point for coordinates.
    """
    stations = []
    try:
        root = ET.fromstring(kml_content)
        for placemark in root.iter(f"{KML_NS}Placemark"):
            # Name: try <name>, then ExtendedData SimpleData POL_STAName
            name = None
            name_elem = placemark.find(f"{KML_NS}name")
            if name_elem is not None and name_elem.text:
                name = name_elem.text.strip()

            for sd in placemark.iter(f"{KML_NS}SimpleData"):
                attr_name = sd.get("name", "")
                if attr_name in ("POL_STAName", "POL_OPSTName", "Name", "name", "OUTPOST_NA") and sd.text:
                    name = sd.text.strip()
                    break

            if not name:
                continue

            # Coordinates: try multiple paths
            coords_text = None
            for coords_elem in placemark.iter(f"{KML_NS}coordinates"):
                if coords_elem.text and coords_elem.text.strip():
                    coords_text = coords_elem.text.strip()
                    break

            if not coords_text:
                continue

            parts = coords_text.split(",")
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                    if (
                        BANGALORE_BBOX["south"] <= lat <= BANGALORE_BBOX["north"]
                        and BANGALORE_BBOX["west"] <= lon <= BANGALORE_BBOX["east"]
                    ):
                        stations.append(
                            {
                                "name": name,
                                "type": station_type,
                                "latitude": lat,
                                "longitude": lon,
                            }
                        )
                except ValueError:
                    pass
    except ET.ParseError:
        pass
    return stations


def fetch():
    all_stations = []

    # Fetch police stations
    print("  Downloading Bengaluru police station locations from data.opencity.in (KSRSAC)...")
    try:
        req = urllib.request.Request(PS_KML_URL, headers={"User-Agent": "bangalore-score/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        kml = resp.read().decode("utf-8")
        ps = _parse_kml_stations(kml, "station")
        print(f"    Police stations: {len(ps)} parsed from KML")
        all_stations.extend(ps)
    except Exception as e:
        print(f"    Warning: Could not fetch police stations KML ({e})")

    # Fetch outposts
    try:
        req = urllib.request.Request(OUTPOST_KML_URL, headers={"User-Agent": "bangalore-score/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        kml = resp.read().decode("utf-8")
        outposts = _parse_kml_stations(kml, "outpost")
        print(f"    Police outposts: {len(outposts)} parsed from KML")
        all_stations.extend(outposts)
    except Exception as e:
        print(f"    Warning: Could not fetch outposts KML ({e})")

    if not all_stations:
        print("  No stations fetched. Keeping existing data.")
        return 0

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM police_stations")
            for s in all_stations:
                cur.execute(
                    """INSERT INTO police_stations (name, type, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (s["name"], s["type"], s["longitude"], s["latitude"]),
                )
        conn.commit()
        print(f"  OK: {len(all_stations)} police stations + outposts seeded from KSRSAC data")
    finally:
        conn.close()

    return len(all_stations)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
