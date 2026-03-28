"""
Fetch slum location data for Bangalore.

Source: Bengaluru Slums Map — data.opencity.in (CC BY, updated Nov 2025)
        CNN satellite imagery classification from:
        "Identifying a Slums' Degree of Deprivation from VHR Images Using CNNs"
        https://www.mdpi.com/2072-4292/11/11/1282

The KML contains ~17,762 placemarks; ~11,291 have actual polygon coordinates.
Each has a DN (deprivation index) field 0-245 from the CNN model (higher = more deprived).
We store polygon + centroid + DN for proximity scoring.
"""

import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from app.db import get_sync_conn

SLUM_KML_URL = (
    "https://data.opencity.in/dataset/8715ed09-23f3-491f-bfcc-fc4ac31194a9/"
    "resource/91bba372-8e8c-4b2c-bbe2-71478f6921e9/download/"
    "7ffce76e-2390-40ad-b6f9-f93c1a5d8c0b.kml"
)

KML_NS = "http://www.opengis.net/kml/2.2"


def _parse_slum_kml(content: str) -> list[dict]:
    """Parse slum placemarks from KML, returning polygons with DN values."""
    records = []
    root = ET.fromstring(content)

    for pm in root.iter(f"{{{KML_NS}}}Placemark"):
        fid_elem = pm.find(f".//{{{KML_NS}}}SimpleData[@name='fid']")
        dn_elem = pm.find(f".//{{{KML_NS}}}SimpleData[@name='DN']")

        fid = int(float(fid_elem.text)) if fid_elem is not None and fid_elem.text else None
        dn = int(float(dn_elem.text)) if dn_elem is not None and dn_elem.text else None

        coords_elem = pm.find(f".//{{{KML_NS}}}coordinates")
        if coords_elem is None or not coords_elem.text or not coords_elem.text.strip():
            continue

        raw_coords = coords_elem.text.strip().split()
        if len(raw_coords) < 3:
            continue

        parsed = []
        for c in raw_coords:
            parts = c.split(",")
            if len(parts) >= 2:
                try:
                    parsed.append((float(parts[0]), float(parts[1])))
                except ValueError:
                    continue

        if len(parsed) < 3:
            continue

        # Ensure ring is closed
        if parsed[0] != parsed[-1]:
            parsed.append(parsed[0])

        lons = [p[0] for p in parsed]
        lats = [p[1] for p in parsed]
        centroid_lon = sum(lons) / len(lons)
        centroid_lat = sum(lats) / len(lats)

        wkt_ring = ", ".join(f"{lon} {lat}" for lon, lat in parsed)
        wkt_polygon = f"POLYGON(({wkt_ring}))"
        wkt_centroid = f"POINT({centroid_lon} {centroid_lat})"

        records.append(
            {
                "fid": fid,
                "dn": dn if dn is not None else 0,
                "polygon_wkt": wkt_polygon,
                "centroid_wkt": wkt_centroid,
            }
        )

    return records


def fetch():
    print("  Downloading Bengaluru Slums Map KML (data.opencity.in)...")
    try:
        req = urllib.request.Request(SLUM_KML_URL, headers={"User-Agent": "bangalore-score/1.0"})
        resp = urllib.request.urlopen(req, timeout=60)
        kml_content = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR: Could not download slum KML: {e}")
        return 0

    records = _parse_slum_kml(kml_content)
    print(f"  Parsed {len(records)} slum polygons with coordinates")

    if not records:
        print("  WARNING: No records parsed from KML")
        return 0

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM slum_zones")

            count = 0
            for r in records:
                try:
                    cur.execute(
                        """INSERT INTO slum_zones (fid, deprivation_dn, geog, centroid_geog)
                           VALUES (%s, %s, ST_GeogFromText(%s), ST_GeogFromText(%s))""",
                        (r["fid"], r["dn"], r["polygon_wkt"], r["centroid_wkt"]),
                    )
                    count += 1
                except Exception:
                    # Skip invalid geometries
                    conn.rollback()
                    continue

        conn.commit()
        print(f"  OK: {count} slum zones inserted")
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    fetch()
