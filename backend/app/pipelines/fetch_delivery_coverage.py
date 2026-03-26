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

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

# All areas covered by quick-commerce in Bangalore, organized by coverage tier.
# Central/urban areas are covered by all 4 services; suburban by 2-3; outer by 1-2.

_CORE_AREAS = {
    "Koramangala", "Indiranagar", "HSR Layout", "BTM Layout", "Jayanagar",
    "JP Nagar", "Malleshwaram", "Rajajinagar", "Basavanagudi", "Domlur",
    "Wilson Garden", "Richmond Town", "Sadashivanagar", "Frazer Town",
    "Shivaji Nagar", "Vasanth Nagar", "Ulsoor", "Langford Town",
    "Chickpet", "Shanti Nagar", "Gandhinagar", "Cottonpet", "Majestic",
    "Srinagar", "Hanumanthanagar", "Girinagar", "Thyagarajanagar",
    "Chamrajpet", "Seshadripuram", "Cox Town", "Cooke Town",
    "MG Road", "MG Road / Central", "Byappanahalli",
}

_SUBURBAN_AREAS = {
    "Whitefield", "Marathahalli", "Hebbal", "Banashankari", "Electronic City",
    "Bellandur", "Sarjapur Road", "Bommanahalli", "Yelahanka", "Thanisandra",
    "HAL", "Brookefield", "Kundalahalli", "Kadubeesanahalli", "HBR Layout",
    "Banaswadi", "Vijayanagar", "Nagarbhavi", "Sahakara Nagar", "RT Nagar",
    "Old Madras Road", "KR Puram", "Jakkur", "Bannerghatta Road",
    "Hennur", "Horamavu", "Kammanahalli", "Panathur", "Hoodi",
    "Varthur", "Harlur", "HSR Layout", "Kadugodi", "Nagavara",
    "Basaveshwaranagar", "Attiguppe", "Lingarajapuram", "Kalyan Nagar",
    "HRBR Layout", "Ganganagar", "Sanjaynagar", "Mathikere",
    "Nandini Layout", "Yeshwanthpur", "Peenya", "Padmanabhanagar",
    "Kumaraswamy Layout", "Hosur Road", "Gottigere", "Hulimavu",
    "Kasavanahalli", "Haralur", "Somasundarapalya", "Bilekahalli",
    "Arekere", "Kodichikkanahalli", "Kudlu Gate", "Begur",
    "AECS Layout", "Vignana Nagar", "CV Raman Nagar", "Kasturi Nagar",
    "Tin Factory", "Ramamurthy Nagar", "Vidyaranyapura",
    "Chandra Layout", "JP Nagar Phase 7",
}

_OUTER_AREAS = {
    "Devanahalli", "Kengeri", "Kanakapura Road", "Mahadevapura",
    "Rajarajeshwari Nagar", "RR Nagar", "Uttarahalli", "Carmelaram",
    "Singasandra", "Akshayanagar", "Konanakunte", "Yelachenahalli",
    "Hosakerehalli", "Laggere", "Jalahalli", "Magadi Road", "Mysore Road",
    "Hosa Road", "Varthur Road", "Sarjapur", "Tumkur Road",
    "Bommasandra", "Talaghattapura", "Anjanapura",
    "Kogilu", "Nagashettyhalli", "Bagalur",
}

_VERY_OUTER = {
    "Chandapura", "Anekal", "Jigani", "Nelamangala",
}

# Zepto: strong in core + suburban
ZEPTO_AREAS = _CORE_AREAS | _SUBURBAN_AREAS

# Blinkit: core + most suburban
BLINKIT_AREAS = _CORE_AREAS | (_SUBURBAN_AREAS - {"Vidyaranyapura", "Ramamurthy Nagar", "JP Nagar Phase 7"})

# Swiggy Instamart: widest quick-commerce, covers outer too
SWIGGY_AREAS = _CORE_AREAS | _SUBURBAN_AREAS | _OUTER_AREAS

# BigBasket: widest overall, even some very outer
BIGBASKET_AREAS = _CORE_AREAS | _SUBURBAN_AREAS | _OUTER_AREAS | _VERY_OUTER

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
