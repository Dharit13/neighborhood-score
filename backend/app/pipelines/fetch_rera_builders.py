"""
Fetch real builder data from RERA Karnataka portal.

Source: rera.karnataka.gov.in — Real Estate Regulatory Authority Karnataka
  - Project registration counts
  - Complaint counts per builder
  - Complaint resolution status

The RERA portal doesn't have a public API, so we scrape complaint report pages
for each builder. Falls back to the existing curated data if scraping fails.

Also adds `avoid_reason` field for builders with poor track records.
"""

import json
import sys
import os
import urllib.request
import urllib.parse
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn
from app.config import CURATED_DIR

RERA_BASE = "https://rera.karnataka.gov.in"

# RERA project search URL template
RERA_SEARCH_URL = RERA_BASE + "/projectViewDetails"


class _ComplaintCountParser(HTMLParser):
    """Extract complaint count from RERA complaint report pages."""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.row_count = 0
        self.complaint_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.row_count += 1

    def handle_endtag(self, tag):
        if tag == "table":
            if self.in_table and self.row_count > 1:
                self.complaint_count = self.row_count - 1  # minus header
            self.in_table = False
            self.row_count = 0


def _fetch_rera_complaints(builder_name):
    """Attempt to fetch complaint count from RERA portal for a builder."""
    try:
        search_url = f"{RERA_BASE}/complaintReportWiseList?pName={urllib.parse.quote(builder_name)}"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        parser = _ComplaintCountParser()
        parser.feed(html)

        return parser.complaint_count if parser.complaint_count > 0 else None
    except Exception:
        return None


def _compute_avoid_reason(builder):
    """Generate avoid reason for problematic builders."""
    reasons = []

    complaints_ratio = builder.get("complaints_ratio", 0)
    on_time = builder.get("on_time_delivery_pct", 100)
    complaints = builder.get("complaints", 0)

    if complaints_ratio > 2.0:
        reasons.append(f"High complaint ratio ({complaints_ratio})")
    if on_time < 65:
        reasons.append(f"Poor delivery record ({on_time}% on-time)")
    if complaints > 15:
        reasons.append(f"{complaints} RERA complaints filed")

    return "; ".join(reasons) if reasons else None


def fetch():
    """Update builder data with RERA portal verification."""
    print("  Checking RERA Karnataka portal for builder data...")

    # Load existing curated data as baseline
    with open(CURATED_DIR / "builders.json") as f:
        data = json.load(f)

    builders = data["builders"]
    updated_count = 0

    for builder in builders:
        name = builder["name"]

        # Attempt RERA portal lookup
        rera_complaints = _fetch_rera_complaints(name)
        if rera_complaints is not None:
            old_complaints = builder["complaints"]
            builder["complaints"] = rera_complaints
            if builder["rera_projects"] > 0:
                builder["complaints_ratio"] = round(rera_complaints / builder["rera_projects"], 2)
            builder["_rera_verified"] = True
            if rera_complaints != old_complaints:
                print(f"    {name}: RERA complaints updated {old_complaints} -> {rera_complaints}")
                updated_count += 1
        else:
            builder["_rera_verified"] = False

        # Compute avoid reason
        builder["_avoid_reason"] = _compute_avoid_reason(builder)

    print(f"  RERA portal: {updated_count} builders updated with live complaint data")

    # Write to database
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM builders")
            for b in builders:
                cur.execute(
                    """INSERT INTO builders
                       (name, rera_projects, total_projects_blr, complaints, complaints_ratio,
                        on_time_delivery_pct, avg_rating, reputation_tier, active_areas, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (name) DO UPDATE SET
                         complaints = EXCLUDED.complaints,
                         complaints_ratio = EXCLUDED.complaints_ratio,
                         score = EXCLUDED.score""",
                    (
                        b["name"], b["rera_projects"], b["total_projects_blr"],
                        b["complaints"], b["complaints_ratio"],
                        b["on_time_delivery_pct"], b["avg_rating"],
                        b["reputation_tier"], b["active_areas"], b["score"],
                    ),
                )
        conn.commit()
        print(f"  OK: {len(builders)} builders seeded (RERA-verified where possible)")
    finally:
        conn.close()

    return len(builders)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fetch()
