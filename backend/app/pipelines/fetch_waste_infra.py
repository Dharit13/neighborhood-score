"""
Fetch BBMP waste management infrastructure data for Bangalore.

Sources (all from data.opencity.in, CC BY, updated Nov 2025):
  - Dry Waste Collection Centres: 336 locations
  - Waste Processing Plants: 8 locations
  - Landfill Locations: 3 locations
  - Biomethanisation Plants: 11 locations
"""

import sys
import os
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.db import get_sync_conn

BASE = "https://data.opencity.in/dataset/c904b267-5369-4aee-990c-dc86047fee3c/resource"

WASTE_KMLS = [
    {
        "type": "dry_waste_centre",
        "label": "Dry Waste Collection Centres",
        "url": f"{BASE}/e6aa9364-b0ab-4b5d-8076-95c45d985599/download/d158fed8-5266-49ee-9122-4920f847c740.kml",
    },
    {
        "type": "waste_processing",
        "label": "Waste Processing Plants",
        "url": f"{BASE}/1845a80c-6fcf-4b3b-b3a0-4283d692a2eb/download/8dbf2d4b-1dcd-4c78-a3ad-eb3a92661e64.kml",
    },
    {
        "type": "landfill",
        "label": "Landfill Locations",
        "url": f"{BASE}/c78b6624-1efe-404a-8303-0efdac451eb7/download/deb891bf-d6aa-46fa-92f9-58ce888a8f9c.kml",
    },
    {
        "type": "biomethanisation",
        "label": "Biomethanisation Plants",
        "url": f"{BASE}/c5b4acd3-3ef5-4da7-bbb6-5c2044b31241/download/fb5c2d41-c293-4924-9147-ced0a7f13a6c.kml",
    },
]

KML_NS = "http://www.opengis.net/kml/2.2"


def _parse_waste_kml(content: str, infra_type: str) -> list[dict]:
    """Parse point locations from a waste infrastructure KML."""
    records = []
    root = ET.fromstring(content)

    for pm in root.iter(f"{{{KML_NS}}}Placemark"):
        name_elem = pm.find(f"{{{KML_NS}}}name")
        name = name_elem.text.strip() if name_elem is not None and name_elem.text else f"{infra_type} (unnamed)"

        # Try Point coordinates first, then any coordinates element
        coords_elem = pm.find(f".//{{{KML_NS}}}Point/{{{KML_NS}}}coordinates")
        if coords_elem is None:
            coords_elem = pm.find(f".//{{{KML_NS}}}coordinates")
        if coords_elem is None or not coords_elem.text:
            continue

        parts = coords_elem.text.strip().split(",")
        if len(parts) < 2:
            continue

        try:
            lon, lat = float(parts[0]), float(parts[1])
        except ValueError:
            continue

        if not (12.5 <= lat <= 13.5 and 77.0 <= lon <= 78.2):
            continue

        records.append({
            "name": name,
            "type": infra_type,
            "lat": lat,
            "lon": lon,
        })

    return records


def fetch():
    print("  Downloading BBMP waste infrastructure KMLs (4 datasets from data.opencity.in)...")
    all_records: list[dict] = []

    for kml_info in WASTE_KMLS:
        try:
            req = urllib.request.Request(kml_info["url"], headers={"User-Agent": "bangalore-score/1.0"})
            resp = urllib.request.urlopen(req, timeout=30)
            content = resp.read().decode("utf-8")
            records = _parse_waste_kml(content, kml_info["type"])
            all_records.extend(records)
            print(f"    {kml_info['label']}: {len(records)} locations parsed")
        except Exception as e:
            print(f"    {kml_info['label']}: Could not fetch ({e})")

    if not all_records:
        print("  WARNING: No waste infrastructure records parsed")
        return 0

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM waste_infrastructure")
            count = 0
            for r in all_records:
                cur.execute(
                    """INSERT INTO waste_infrastructure (name, type, geog)
                       VALUES (%s, %s, ST_Point(%s, %s)::geography)""",
                    (r["name"], r["type"], r["lon"], r["lat"]),
                )
                count += 1

        conn.commit()
        print(f"  OK: {count} waste infrastructure locations inserted")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fetch()
