"""
Fetch real BMTC bus stop data from two sources:
  1. data.opencity.in — 9,600 bus stops KML (authoritative BMTC data, CC BY)
  2. iotakodali/bmtc-realtime-api GitHub — 9,068 stops CSV (BMTC GTFS, fallback)

Filters to Bangalore metro area bounding box and inserts into bus_stops table.
"""

import csv
import io
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import BANGALORE_BBOX
from app.db import get_sync_conn

# Primary: data.opencity.in — 9,600 BMTC bus stop locations (KML)
OPENCITY_KML_URL = "https://data.opencity.in/dataset/8bcca4f2-7392-4ecb-ba1e-28dccd987c34/resource/c8fda6d4-0caa-40ec-ab5a-236984974745/download/bmtc_bus_stops.kml"
# Fallback: GitHub CSV with 9,068 stops
GITHUB_CSV_URL = "https://raw.githubusercontent.com/iotakodali/bmtc-realtime-api/master/stops/stops.csv"


def _parse_kml_stops(kml_content):
    """Parse bus stop coordinates and names from KML."""
    stops = []
    try:
        root = ET.fromstring(kml_content)
        for placemark in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
            name_elem = placemark.find("{http://www.opengis.net/kml/2.2}name")
            name = name_elem.text.strip() if name_elem is not None and name_elem.text else "Unknown"

            coords = placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates")
            if coords is not None and coords.text:
                parts = coords.text.strip().split(",")
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        stops.append({"name": name, "latitude": lat, "longitude": lon})
                    except ValueError:
                        pass
    except ET.ParseError:
        pass
    return stops


def _parse_csv_stops(csv_content):
    """Parse bus stops from GitHub CSV."""
    reader = csv.DictReader(io.StringIO(csv_content))
    stops = []
    for row in reader:
        try:
            lat = float(row["lat"])
            lng = float(row["lng"])
            name = row.get("stopa_name", row.get("stop_name", "Unknown")).strip()
            stops.append({"stop_id": row.get("stop_id", ""), "name": name, "latitude": lat, "longitude": lng})
        except (ValueError, KeyError):
            continue
    return stops


def _filter_bbox(stops):
    """Filter stops to Bangalore bounding box."""
    return [
        s
        for s in stops
        if (
            BANGALORE_BBOX["south"] <= s["latitude"] <= BANGALORE_BBOX["north"]
            and BANGALORE_BBOX["west"] <= s["longitude"] <= BANGALORE_BBOX["east"]
        )
    ]


def fetch():
    stops = []

    # Try data.opencity.in KML first (9,600 stops, authoritative)
    print("  Downloading BMTC bus stops from data.opencity.in (9,600 stops KML)...")
    try:
        req = urllib.request.Request(OPENCITY_KML_URL, headers={"User-Agent": "bangalore-score/1.0"})
        resp = urllib.request.urlopen(req, timeout=60)
        kml_content = resp.read().decode("utf-8")
        stops = _parse_kml_stops(kml_content)
        print(f"  Parsed {len(stops)} stops from data.opencity.in KML")
    except Exception as e:
        print(f"  data.opencity.in failed ({e}), trying GitHub fallback...")

    # Fallback to GitHub CSV
    if len(stops) < 100:
        print("  Downloading BMTC bus stops from GitHub CSV (9,068 stops)...")
        try:
            resp = urllib.request.urlopen(GITHUB_CSV_URL, timeout=60)
            csv_content = resp.read().decode("utf-8")
            stops = _parse_csv_stops(csv_content)
            print(f"  Parsed {len(stops)} stops from GitHub CSV")
        except Exception as e:
            print(f"  GitHub CSV also failed ({e})")

    stops = _filter_bbox(stops)
    print(f"  {len(stops)} stops within Bangalore bbox")

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bus_stops")
            for s in stops:
                cur.execute(
                    """INSERT INTO bus_stops (stop_id, name, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (s.get("stop_id"), s["name"], s["longitude"], s["latitude"]),
                )
        conn.commit()
        print(f"  OK: {len(stops)} BMTC bus stops seeded")
    finally:
        conn.close()

    return len(stops)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
