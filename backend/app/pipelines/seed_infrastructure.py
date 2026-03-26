"""
Seed infrastructure_projects table with enhanced data including
realistic ETAs computed from historical delay multipliers.

Delay multipliers (from research on Bangalore infra delivery):
  Metro:
    announced -> 5x
    land_acquisition -> 2.5x
    construction -> 1.8x
    testing -> 1.3x
  Ring road / expressway:
    announced -> 6x
    land_acquisition -> 3.5x
    construction -> 2x
  Suburban rail:
    announced -> 4x
    construction -> 3x (adjusted for L&T exit / re-tendering)
  Highway:
    construction -> 1.5x
    land_acquisition -> 2.5x

Sources: News research as of March 2026
"""

import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

DELAY_MULTIPLIERS = {
    "metro": {
        "announced": 5.0,
        "land_acquisition": 2.5,
        "construction": 1.8,
        "testing": 1.3,
        "operational": 1.0,
    },
    "expressway": {
        "announced": 6.0,
        "land_acquisition": 3.5,
        "construction": 2.0,
        "testing": 1.2,
        "operational": 1.0,
    },
    "suburban_rail": {
        "announced": 4.0,
        "land_acquisition": 3.0,
        "construction": 3.0,  # Adjusted for K-RIDE re-tendering
        "testing": 1.5,
        "operational": 1.0,
    },
    "highway": {
        "announced": 4.0,
        "land_acquisition": 2.5,
        "construction": 1.5,
        "operational": 1.0,
    },
    "flyover": {
        "announced": 3.0,
        "land_acquisition": 2.0,
        "construction": 1.5,
        "testing": 1.1,
        "operational": 1.0,
    },
}

PROJECTS = [
    {
        "name": "Namma Metro Phase 2A — Blue Line (Silk Board to KR Puram)",
        "type": "metro",
        "source_agency": "BMRCL",
        "official_completion_date": "2026-06-30",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 82.0,
        "length_km": 18.8,
        "route_description": "ORR Blue Line extension: Silk Board - HSR Layout - Bellandur - Marathahalli - KR Puram, 13 stations",
        "affected_areas": ["Silk Board", "HSR Layout", "Bellandur", "Marathahalli", "Mahadevapura", "KR Puram", "Sarjapur Road", "Kadubeesanahalli"],
        "prediction_confidence": "medium",
        "prediction_rationale": "82% complete, viaduct done on most stretches. BMRCL targets June 2026 opening. Station finishing work ongoing.",
        "last_progress_update": "2026-03-25",
    },
    {
        "name": "Namma Metro Phase 2B — Nagawara to Airport",
        "type": "metro",
        "source_agency": "BMRCL",
        "official_completion_date": "2027-12-31",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 45.0,
        "length_km": 38.4,
        "route_description": "Blue Line extension north: KR Puram corridor to Nagawara, then Hebbal - Yelahanka - Airport. Includes Pink Line (Nagawara-Gottigere)",
        "affected_areas": ["KR Puram", "Kalyan Nagar", "Nagawara", "Hebbal", "Yelahanka", "Devanahalli", "Thanisandra", "Hennur"],
        "prediction_confidence": "low",
        "prediction_rationale": "45% complete, pier work 59-96% by section. Track plinth barely started. Pink Line 95% tunnel done, Dec 2026 target.",
        "last_progress_update": "2026-03-01",
    },
    {
        "name": "Namma Metro Phase 3 — ORR Line",
        "type": "metro",
        "source_agency": "BMRCL",
        "official_completion_date": "2032-12-31",
        "current_status": "planning",
        "current_phase": "announced",
        "completion_percentage": 0.0,
        "length_km": 80.0,
        "route_description": "Orbital ORR line: Hebbal - Yeshwanthpur - Banashankari - JP Nagar - HSR Layout - Silk Board, completing the ring",
        "affected_areas": ["Hebbal", "Yeshwanthpur", "Rajajinagar", "Banashankari", "JP Nagar", "BTM Layout", "HSR Layout", "Silk Board"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "Still in planning/DPR stage. 5x multiplier on announced timelines for Bangalore metro historically.",
        "last_progress_update": "2026-01-01",
    },
    {
        "name": "Bengaluru Business Corridor (Peripheral Ring Road)",
        "type": "expressway",
        "source_agency": "BDA",
        "official_completion_date": "2030-12-31",
        "current_status": "land_acquisition",
        "current_phase": "land_acquisition",
        "completion_percentage": 5.0,
        "length_km": 74.0,
        "cost_crore": 27000,
        "route_description": "8-lane expressway (rebranded from PRR) with 5m median for future metro. Tumkur Road to Bellary Road section tendering first.",
        "affected_areas": ["Whitefield", "Sarjapur Road", "Electronic City", "Bannerghatta Road", "Kanakapura Road", "Mysore Road", "Tumkur Road", "Yelahanka"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "50% land acquisition done for first 23km stretch. Project stalled for 20 years, recently rebranded. 3.5x multiplier.",
        "last_progress_update": "2026-02-01",
    },
    {
        "name": "Bengaluru Suburban Rail — Mallige Line",
        "type": "suburban_rail",
        "source_agency": "K-RIDE",
        "official_completion_date": "2028-06-30",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 30.0,
        "length_km": 25.0,
        "route_description": "Benniganahalli - Nagawara - Hebbal - Yeshwanthpur - Chikkabanavara. Elevated + at-grade.",
        "affected_areas": ["KR Puram", "Kalyan Nagar", "Nagawara", "Hebbal", "Yeshwanthpur", "Malleshwaram"],
        "prediction_confidence": "low",
        "prediction_rationale": "L&T terminated contracts unilaterally. K-RIDE re-tendering in 3 packages (18-24 month deadlines). 90% land acquired. 30% construction done.",
        "last_progress_update": "2026-02-01",
    },
    {
        "name": "Bengaluru Suburban Rail — Kanaka Line",
        "type": "suburban_rail",
        "source_agency": "K-RIDE",
        "official_completion_date": "2027-12-31",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 20.0,
        "length_km": 35.0,
        "route_description": "KSR Bengaluru - Cantonment - Baiyappanahalli - KR Puram - Whitefield",
        "affected_areas": ["Majestic", "Cantonment", "Baiyappanahalli", "KR Puram", "Whitefield"],
        "prediction_confidence": "low",
        "prediction_rationale": "Same L&T exit impacts. Fresh tenders being floated. 3x multiplier on new timelines.",
        "last_progress_update": "2026-02-01",
    },
    {
        "name": "STRR — Satellite Town Ring Road",
        "type": "expressway",
        "source_agency": "NHAI / KRDCL",
        "official_completion_date": "2027-06-30",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 70.0,
        "length_km": 280.0,
        "route_description": "280 km ring connecting satellite towns. 21 km stretch near completion linking to Bengaluru-Chennai Expressway.",
        "affected_areas": ["Devanahalli", "Hoskote", "Anekal", "Nelamangala"],
        "prediction_confidence": "medium",
        "prediction_rationale": "21km section nearly complete. Full ring road will take much longer. 2x for remaining sections.",
        "last_progress_update": "2026-01-01",
    },
    {
        "name": "KR Puram - Silk Board Elevated Corridor",
        "type": "highway",
        "source_agency": "BBMP / NHAI",
        "official_completion_date": "2028-12-31",
        "current_status": "planning",
        "current_phase": "land_acquisition",
        "completion_percentage": 0.0,
        "length_km": 15.0,
        "route_description": "Elevated corridor on ORR from KR Puram to Silk Board to ease chronic congestion",
        "affected_areas": ["KR Puram", "Marathahalli", "Bellandur", "Silk Board", "Whitefield"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "Overlap with Metro Phase 2A on same corridor. Timeline uncertain. May be deprioritized.",
        "last_progress_update": "2025-06-01",
    },
    # ── New projects added March 2026 ──
    {
        "name": "Namma Metro Pink Line (Kalena Agrahara — Nagawara)",
        "type": "metro",
        "source_agency": "BMRCL",
        "official_completion_date": "2026-12-31",
        "current_status": "construction",
        "current_phase": "testing",
        "completion_percentage": 90.0,
        "length_km": 21.25,
        "route_description": "North-south line: Kalena Agrahara - Bannerghatta Road - JP Nagar - Jayanagar - Lalbagh - MG Road - Shivajinagar - Nagawara. 18 stations (12 underground, 6 elevated). Phase 1 elevated (7.5 km) opening May 2026, full corridor Dec 2026.",
        "affected_areas": ["Bannerghatta Road", "JP Nagar", "Jayanagar", "Basavanagudi", "MG Road / Central", "Shivajinagar", "Nagawara", "Gottigere", "Hulimavu"],
        "prediction_confidence": "high",
        "prediction_rationale": "Trial runs started March 2026 on elevated stretch. RDSO safety trials completing. 95% tunnel boring done. Phase 1 opening May 2026 is highly likely.",
        "last_progress_update": "2026-03-25",
    },
    {
        "name": "Namma Metro Yellow Line (RV Road — Bommasandra)",
        "type": "metro",
        "source_agency": "BMRCL",
        "official_completion_date": "2025-08-01",
        "current_status": "operational",
        "current_phase": "operational",
        "completion_percentage": 100.0,
        "length_km": 18.82,
        "route_description": "Fully operational since August 2025. RV Road - Ragigudda - Jayadeva - BTM Layout - Silk Board - HSR Layout - Electronic City - Bommasandra. 16 stations. 10-min peak frequency.",
        "affected_areas": ["Banashankari", "BTM Layout", "Silk Board", "HSR Layout", "Electronic City", "Bommasandra", "Arekere", "Singasandra", "Kudlu Gate"],
        "prediction_confidence": "high",
        "prediction_rationale": "Fully operational. No construction risk. Direct impact on property values along corridor already visible.",
        "last_progress_update": "2026-03-25",
    },
    {
        "name": "Bengaluru Suburban Rail — Parijaata Line",
        "type": "suburban_rail",
        "source_agency": "K-RIDE",
        "official_completion_date": "2029-12-31",
        "current_status": "planning",
        "current_phase": "announced",
        "completion_percentage": 5.0,
        "length_km": 45.0,
        "route_description": "Baiyappanahalli - Hosur corridor. Part of the 160 km Bengaluru Suburban Railway network. DPR stage.",
        "affected_areas": ["Baiyappanahalli", "Electronic City", "Hosur Road", "Bommasandra", "Anekal"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "Still in planning/DPR stage. K-RIDE facing contractor issues across all lines. 4x multiplier on announced timelines.",
        "last_progress_update": "2026-01-01",
    },
    {
        "name": "Bengaluru-Chennai Expressway",
        "type": "expressway",
        "source_agency": "NHAI",
        "official_completion_date": "2026-07-31",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 65.0,
        "length_km": 263.0,
        "cost_crore": 17000,
        "route_description": "4-lane access-controlled greenfield expressway. Karnataka section (Hoskote to Bethamangala, 71 km) complete since Dec 2024. AP and TN sections under construction. Reduces Bengaluru-Chennai travel from 6-8 hrs to 2-3 hrs.",
        "affected_areas": ["Hoskote", "Old Madras Road", "KR Puram", "Whitefield"],
        "prediction_confidence": "medium",
        "prediction_rationale": "Karnataka section done. 3 of 4 AP/TN packages at 90%. One package stalled due to concessionaire financial issues. July 2026 target for full opening.",
        "last_progress_update": "2026-03-01",
    },
    {
        "name": "Bengaluru-Mysuru Expressway",
        "type": "expressway",
        "source_agency": "NHAI",
        "official_completion_date": "2023-03-01",
        "current_status": "operational",
        "current_phase": "operational",
        "completion_percentage": 100.0,
        "length_km": 118.0,
        "cost_crore": 8480,
        "route_description": "10-lane access-controlled expressway. NICE Road junction near Kengeri to Mysuru. Fully operational. Reduces travel time from 3 hrs to 75 min.",
        "affected_areas": ["Kengeri", "Mysore Road", "Rajarajeshwari Nagar"],
        "prediction_confidence": "high",
        "prediction_rationale": "Fully operational. Boosting property values along the Mysuru Road corridor and satellite towns.",
        "last_progress_update": "2026-03-25",
    },
    {
        "name": "Major Arterial Road (Magadi Road — Mysuru Road)",
        "type": "highway",
        "source_agency": "BDA",
        "official_completion_date": "2026-03-31",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 90.0,
        "length_km": 10.75,
        "route_description": "6-lane arterial connecting Magadi Road and Mysuru Road. Full 6-lane opening by end of March 2026.",
        "affected_areas": ["Magadi Road", "Mysore Road", "Vijayanagar", "Rajajinagar", "Chandra Layout", "Attiguppe"],
        "prediction_confidence": "high",
        "prediction_rationale": "90% done. BDA confirmed full 6-lane opening by March-end 2026. Minor finishing work remains.",
        "last_progress_update": "2026-03-01",
    },
    {
        "name": "Silk Board Double-Decker Flyover",
        "type": "flyover",
        "source_agency": "BMRCL / BBMP",
        "official_completion_date": "2026-03-31",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 95.0,
        "length_km": 5.12,
        "cost_crore": 449,
        "route_description": "Double-decker flyover along Yellow Line metro viaduct. Ragigudda to Silk Board junction. One side opened June 2024. Remaining ramps D & E (1.37 km) connecting HSR Layout, Ragigudda, BTM Layout completing March 2026.",
        "affected_areas": ["Silk Board", "HSR Layout", "BTM Layout", "Koramangala", "Bannerghatta Road"],
        "prediction_confidence": "high",
        "prediction_rationale": "95% done. Officials confirmed finishing works by March 22, full opening March-end 2026.",
        "last_progress_update": "2026-03-15",
    },
    {
        "name": "Yelahanka Flyover",
        "type": "flyover",
        "source_agency": "GBA / BBMP",
        "official_completion_date": "2026-09-30",
        "current_status": "construction",
        "current_phase": "construction",
        "completion_percentage": 70.0,
        "length_km": 2.0,
        "route_description": "Elevated corridor on Doddaballapur Main Road, Yelahanka. 51 of 56 pillars done, 351 of 447 segments erected. Night construction due to traffic.",
        "affected_areas": ["Yelahanka", "Jakkur", "Vidyaranyapura", "Sahakara Nagar"],
        "prediction_confidence": "medium",
        "prediction_rationale": "70% done. GBA chief says September 2026. Earlier deadline was May 2026 (missed). 1.3x multiplier.",
        "last_progress_update": "2026-02-01",
    },
    {
        "name": "ORR Transformation — Silk Board to KR Puram",
        "type": "highway",
        "source_agency": "BBMP / GBA",
        "official_completion_date": "2028-12-31",
        "current_status": "planning",
        "current_phase": "announced",
        "completion_percentage": 0.0,
        "length_km": 20.0,
        "cost_crore": 450,
        "route_description": "Global-standard corridor upgrade of Outer Ring Road from Silk Board to KR Puram. Pedestrian walkways, EV charging, cycling lanes, landscaping. Part of 2026-27 budget allocation.",
        "affected_areas": ["Silk Board", "Bellandur", "Marathahalli", "Mahadevapura", "KR Puram", "Whitefield", "Kadubeesanahalli", "Domlur"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "Budget announced but no construction started. ORR is already congested. 2.5x multiplier on announced timeline.",
        "last_progress_update": "2026-03-01",
    },
    {
        "name": "BBC-1 Tunnel Road",
        "type": "expressway",
        "source_agency": "BDA / KRDCL",
        "official_completion_date": "2035-12-31",
        "current_status": "planning",
        "current_phase": "announced",
        "completion_percentage": 0.0,
        "length_km": 73.0,
        "cost_crore": 40000,
        "route_description": "Underground tunnel road component of Bengaluru Business Corridor. 73 km tunnel connecting key corridors. Land acquisition for surface BBC complete. Tunnel DPR being prepared.",
        "affected_areas": ["Hebbal", "Yeshwanthpur", "Rajajinagar", "Banashankari", "JP Nagar", "Silk Board", "Whitefield", "Electronic City", "Sarjapur Road"],
        "prediction_confidence": "very_low",
        "prediction_rationale": "₹40,000 Cr mega project still in DPR stage. Bangalore has never built a road tunnel. 6x multiplier minimum. Unlikely before 2040.",
        "last_progress_update": "2026-03-01",
    },
    {
        "name": "Namma Metro Pedestrian Walkway (ORR Viaduct)",
        "type": "highway",
        "source_agency": "BMRCL / BBMP",
        "official_completion_date": "2027-12-31",
        "current_status": "planning",
        "current_phase": "announced",
        "completion_percentage": 0.0,
        "length_km": 9.0,
        "cost_crore": 160,
        "route_description": "9 km pedestrian and cycling walkway along the metro viaduct and Outer Ring Road. Part of 2026-27 budget. Will transform ORR walkability.",
        "affected_areas": ["Silk Board", "HSR Layout", "Bellandur", "Marathahalli", "Mahadevapura"],
        "prediction_confidence": "low",
        "prediction_rationale": "Budget allocated but no construction started. Depends on Metro Phase 2A completion. 2x multiplier.",
        "last_progress_update": "2026-03-01",
    },
]


def _compute_realistic_eta(project: dict) -> tuple[str, str]:
    """
    Compute realistic completion date range using delay multipliers.

    Returns (low_date, high_date) as ISO date strings.
    """
    official_str = project["official_completion_date"]
    official_date = datetime.strptime(official_str, "%Y-%m-%d")
    now = datetime.now()

    remaining_months = max(1, (official_date - now).days / 30)
    project_type = project["type"]
    phase = project.get("current_phase", "construction")

    multipliers = DELAY_MULTIPLIERS.get(project_type, DELAY_MULTIPLIERS["highway"])
    multiplier = multipliers.get(phase, 1.8)

    completion_pct = project.get("completion_percentage", 0) / 100
    adjusted_multiplier = multiplier * (1 - completion_pct * 0.5)
    adjusted_multiplier = max(1.0, adjusted_multiplier)

    realistic_months = remaining_months * adjusted_multiplier

    low_date = now + timedelta(days=realistic_months * 28)
    high_date = now + timedelta(days=realistic_months * 35)

    return low_date.strftime("%Y-%m-%d"), high_date.strftime("%Y-%m-%d")


def seed():
    """Seed infrastructure_projects table with enhanced data."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM infrastructure_projects")

            for project in PROJECTS:
                low_eta, high_eta = _compute_realistic_eta(project)

                multipliers: dict = DELAY_MULTIPLIERS.get(project["type"], {})  # type: ignore[assignment]
                delay_mult = multipliers.get(project.get("current_phase", "construction"), 1.8)

                cur.execute(
                    """INSERT INTO infrastructure_projects
                       (name, type, source_agency,
                        official_completion_date, realistic_completion_date_low,
                        realistic_completion_date_high, prediction_confidence,
                        prediction_rationale, completion_percentage,
                        current_status, current_phase, last_progress_update,
                        affected_areas, route_description, length_km,
                        cost_crore, delay_multiplier)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        project["name"],
                        project["type"],
                        project["source_agency"],
                        project["official_completion_date"],
                        low_eta,
                        high_eta,
                        project["prediction_confidence"],
                        project["prediction_rationale"],
                        project["completion_percentage"],
                        project["current_status"],
                        project["current_phase"],
                        project.get("last_progress_update"),
                        project["affected_areas"],
                        project["route_description"],
                        project.get("length_km"),
                        project.get("cost_crore"),
                        delay_mult,
                    ),
                )

                print(f"  {project['name']}")
                print(f"    Official: {project['official_completion_date']} | Realistic: {low_eta} to {high_eta}")
                print(f"    Status: {project['current_status']} ({project['completion_percentage']}%) | Multiplier: {delay_mult}x")

        conn.commit()
        print(f"\n  OK: {len(PROJECTS)} infrastructure projects seeded")
        return len(PROJECTS)
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    seed()
