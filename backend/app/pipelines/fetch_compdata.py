"""
Fetch company/director data from CompData API.

Source: compdata.in (MCA Company Master Data API)
  - Company master data by CIN: status, capital, charges, directors
  - Director profile by DIN: other directorships, flag failed companies

API: POST https://technowire.in:5000/capi (company)
     POST https://technowire.in:5000/directorProfile (director)

Requires: COMPDATA_API_KEY and COMPDATA_PASSWORD from registration on msmeintelligence.in

Falls back to storing placeholders if API is unavailable —
the curated builder data continues to work without this enrichment.
"""

import json
import sys
import os
import time
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

logger = logging.getLogger(__name__)

COMPDATA_API_KEY = os.getenv("COMPDATA_API_KEY", "")
COMPDATA_PASSWORD = os.getenv("COMPDATA_PASSWORD", "")
COMPDATA_COMPANY_URL = "https://technowire.in:5000/capi"
COMPDATA_DIRECTOR_URL = "https://technowire.in:5000/directorProfile"

FAILED_STATUSES = {
    "struck off", "under process of striking off",
    "under liquidation", "liquidated", "dormant",
    "amalgamated", "dissolved",
}


def _fetch_company_data(cin: str) -> dict | None:
    """Fetch company master data from CompData API."""
    if not COMPDATA_API_KEY:
        logger.info("COMPDATA_API_KEY not set — skipping CompData API")
        return None

    try:
        import httpx
        resp = httpx.post(
            COMPDATA_COMPANY_URL,
            json={"cin": cin, "key": COMPDATA_API_KEY, "password": COMPDATA_PASSWORD},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success" or data.get("company_name"):
                return data
        logger.warning(f"CompData API returned {resp.status_code} for CIN {cin}")
    except Exception as e:
        logger.warning(f"CompData API failed for CIN {cin}: {e}")

    return None


def _fetch_director_profile(din: str) -> dict | None:
    """Fetch director profile from CompData API."""
    if not COMPDATA_API_KEY:
        return None

    try:
        import httpx
        resp = httpx.post(
            COMPDATA_DIRECTOR_URL,
            json={"din": din, "key": COMPDATA_API_KEY, "password": COMPDATA_PASSWORD},
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.warning(f"CompData director lookup failed for DIN {din}: {e}")

    return None


def _check_director_risk(din: str) -> tuple[bool, str]:
    """Check if a director is linked to failed/struck-off companies."""
    profile = _fetch_director_profile(din)
    if not profile:
        return False, ""

    failed_companies = []
    directorships = profile.get("directorships", profile.get("other_companies", []))
    if isinstance(directorships, list):
        for company in directorships:
            status = (company.get("status") or company.get("company_status") or "").lower()
            if status in FAILED_STATUSES:
                failed_companies.append(f"{company.get('company_name', 'Unknown')} ({status})")

    if failed_companies:
        return True, f"Director linked to: {'; '.join(failed_companies[:3])}"

    return False, ""


def enrich_builders():
    """Enrich all builders that have CINs with CompData company/director data."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, cin, director_dins
                   FROM builders
                   WHERE cin IS NOT NULL AND cin != ''"""
            )
            rows = cur.fetchall()

            if not rows:
                print("  No builders have CINs set. Enrich builders.json with CINs first.")
                print("  You can find CINs at zaubacorp.com by searching builder company names.")
                return 0

            enriched = 0
            for builder_id, name, cin, existing_dins in rows:
                print(f"  Fetching CompData for: {name} (CIN: {cin})")

                company = _fetch_company_data(cin)
                if not company:
                    print(f"    Skipped — API unavailable or CIN not found")
                    time.sleep(1)
                    continue

                # Extract fields
                status = company.get("company_status") or company.get("status", "")
                auth_capital = company.get("authorized_capital")
                paid_capital = company.get("paid_up_capital")
                charges = company.get("charges_count") or company.get("charges", 0)
                inc_date = company.get("date_of_incorporation")

                # Extract directors
                directors = company.get("directors", [])
                director_names = [d.get("name", "") for d in directors if d.get("name")]
                director_dins = [d.get("din", "") for d in directors if d.get("din")]

                # Check director risk
                has_risk = False
                risk_details = ""
                for din in director_dins[:5]:  # Limit API calls
                    risky, detail = _check_director_risk(din)
                    if risky:
                        has_risk = True
                        risk_details += detail + "; "
                    time.sleep(0.5)

                # Update database
                cur.execute(
                    """UPDATE builders SET
                         company_status = %s,
                         authorized_capital = %s,
                         paid_up_capital = %s,
                         charges_registered = %s,
                         incorporated_date = %s,
                         director_names = %s,
                         director_dins = %s,
                         directors_linked_to_failed = %s,
                         director_risk_details = %s,
                         data_last_refreshed = now()
                       WHERE id = %s""",
                    (
                        status,
                        int(auth_capital) if auth_capital else None,
                        int(paid_capital) if paid_capital else None,
                        int(charges) if charges else 0,
                        inc_date,
                        director_names,
                        director_dins,
                        has_risk,
                        risk_details.rstrip("; ") if risk_details else None,
                        builder_id,
                    ),
                )
                enriched += 1
                print(f"    OK: status={status}, directors={len(director_names)}, risk={'YES' if has_risk else 'no'}")
                time.sleep(2)

        conn.commit()
        print(f"\n  Enriched {enriched} builders with CompData")
        return enriched
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    enrich_builders()
