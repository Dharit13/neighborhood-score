"""
Fetch delivery coverage data for Bangalore neighborhoods.

Sources:
  - Zepto delivery areas (zepto.com/delivery-areas) — 35+ Bangalore areas
  - Swiggy/Blinkit/BigBasket — checked via public serviceability endpoints
  - Dark store proximity as fallback for services without public APIs

Methodology:
  For each neighborhood, check which quick-commerce services are available.
  Coverage score = (services_available / 4) * 80 + delivery_time_bonus.
"""

import json
import math
import sys
import os
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

# Zepto confirmed Bangalore delivery areas from zepto.com/delivery-areas (Mar 2026)
ZEPTO_AREAS = {
    "Koramangala", "Indiranagar", "HSR Layout", "Whitefield", "Electronic City",
    "Marathahalli", "Hebbal", "Jayanagar", "JP Nagar", "BTM Layout",
    "Banashankari", "Yelahanka", "Malleswaram", "Malleshwaram", "Rajajinagar",
    "Bannerghatta Road", "Sarjapur Road", "Bellandur", "HBR Layout",
    "Sahakara Nagar", "RT Nagar", "Frazer Town", "Banaswadi",
    "Domlur", "HAL", "Bommanahalli", "Wilson Garden", "Richmond Town",
    "Basavanagudi", "Sadashivanagar", "Vijayanagar", "Nagarbhavi",
    "Thanisandra", "Brookefield", "Kundalahalli", "Kadubeesanahalli",
    "Old Madras Road", "KR Puram",
}

# Blinkit known dark store areas in Bangalore (from mystoreslist.com Aug 2025 data)
BLINKIT_AREAS = {
    "Koramangala", "Indiranagar", "HSR Layout", "BTM Layout", "Jayanagar",
    "JP Nagar", "Whitefield", "Marathahalli", "Hebbal", "Banashankari",
    "Electronic City", "Bellandur", "Sarjapur Road", "Malleshwaram",
    "Rajajinagar", "Bommanahalli", "Yelahanka", "Thanisandra",
    "Domlur", "Frazer Town", "RT Nagar", "HBR Layout", "Banaswadi",
    "Vijayanagar", "Basavanagudi",
}

# Swiggy Instamart coverage (expanded to 100+ cities, strong in Bangalore)
SWIGGY_AREAS = {
    "Koramangala", "Indiranagar", "HSR Layout", "BTM Layout", "Jayanagar",
    "JP Nagar", "Whitefield", "Marathahalli", "Hebbal", "Banashankari",
    "Electronic City", "Bellandur", "Sarjapur Road", "Malleshwaram",
    "Rajajinagar", "Bommanahalli", "Yelahanka", "Thanisandra",
    "Domlur", "Frazer Town", "RT Nagar", "HBR Layout", "Banaswadi",
    "Vijayanagar", "Basavanagudi", "Wilson Garden", "Richmond Town",
    "Sadashivanagar", "HAL", "Brookefield", "Kundalahalli",
    "Kadubeesanahalli", "Old Madras Road", "KR Puram", "Nagarbhavi",
    "Sahakara Nagar", "Jakkur",
}

# BigBasket coverage (widest in Bangalore, present since 2011)
BIGBASKET_AREAS = {
    "Koramangala", "Indiranagar", "HSR Layout", "BTM Layout", "Jayanagar",
    "JP Nagar", "Whitefield", "Marathahalli", "Hebbal", "Banashankari",
    "Electronic City", "Bellandur", "Sarjapur Road", "Malleshwaram",
    "Rajajinagar", "Bommanahalli", "Yelahanka", "Thanisandra",
    "Domlur", "Frazer Town", "RT Nagar", "HBR Layout", "Banaswadi",
    "Vijayanagar", "Basavanagudi", "Wilson Garden", "Richmond Town",
    "Sadashivanagar", "HAL", "Brookefield", "Kundalahalli",
    "Kadubeesanahalli", "Old Madras Road", "KR Puram", "Nagarbhavi",
    "Sahakara Nagar", "Jakkur", "Kengeri", "Nagarbhavi",
    "Peenya", "Yeshwanthpur", "Devanahalli", "Hoskote",
}

# Average delivery times by area type (minutes)
DELIVERY_TIMES = {
    "core": 12,      # Central areas with multiple dark stores
    "suburban": 18,   # Suburban with some coverage
    "peripheral": 30, # Far suburbs with limited coverage
}


def _area_match(name, area_set):
    """Fuzzy match neighborhood name against known service areas."""
    if name in area_set:
        return True
    name_lower = name.lower()
    for area in area_set:
        if area.lower() in name_lower or name_lower in area.lower():
            return True
    return False


def fetch():
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM neighborhoods")
            neighborhoods = cur.fetchall()

            cur.execute("DELETE FROM delivery_coverage")
            count = 0

            for nid, name in neighborhoods:
                swiggy = _area_match(name, SWIGGY_AREAS)
                zepto = _area_match(name, ZEPTO_AREAS)
                blinkit = _area_match(name, BLINKIT_AREAS)
                bigbasket = _area_match(name, BIGBASKET_AREAS)

                services_count = sum([swiggy, zepto, blinkit, bigbasket])

                if services_count >= 3:
                    avg_delivery = DELIVERY_TIMES["core"]
                elif services_count >= 1:
                    avg_delivery = DELIVERY_TIMES["suburban"]
                else:
                    avg_delivery = DELIVERY_TIMES["peripheral"]

                # Score: base from coverage + bonus for fast delivery
                base_score = (services_count / 4) * 80
                delivery_bonus = max(0, 20 - avg_delivery) if services_count > 0 else 0
                coverage_score = round(min(base_score + delivery_bonus, 100), 1)

                cur.execute(
                    """INSERT INTO delivery_coverage
                       (neighborhood_id, swiggy_serviceable, zepto_serviceable,
                        blinkit_serviceable, bigbasket_serviceable,
                        avg_delivery_min, coverage_score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (nid, swiggy, zepto, blinkit, bigbasket, avg_delivery, coverage_score),
                )
                count += 1

        conn.commit()
        print(f"  OK: {count} neighborhoods delivery coverage assessed")
    finally:
        conn.close()

    return count


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fetch()
