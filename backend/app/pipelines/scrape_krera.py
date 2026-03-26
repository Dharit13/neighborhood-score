"""
Scrape Karnataka RERA portal for builder and project data at scale.

Two-phase approach:
  Phase 1 — Discovery: hit /complaintReportWiseList with blank pName to
  get ALL complaints filed. Extract every unique promoter name. Builders
  with complaints are the ones buyers need to know about.

  Phase 2 — Enrichment: for each discovered promoter (+ curated baseline),
  fetch detailed complaint data, compute trust scores, upsert to DB.

The curated 25 in builders.json are the known-good baseline.
Discovery adds the notorious builders that have RERA complaints.

Rate limiting: 2s between requests. Retry 3x with backoff.
"""

import json
import re
import sys
import os
import time
import logging
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Optional
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn
from app.config import CURATED_DIR

logger = logging.getLogger(__name__)

RERA_BASE = "https://rera.karnataka.gov.in"
RATE_LIMIT_SECONDS = 2
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class _ComplaintTableParser(HTMLParser):
    """Parse complaint list pages to extract complaint details."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self.cell_text = ""
        self.table_count = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_count += 1
            if self.table_count == 1:
                self.in_table = True
        if self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        if self.in_row and tag == "td":
            self.in_cell = True
            self.cell_text = ""

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.cell_text)
        if tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        if tag == "table" and self.in_table:
            self.in_table = False


class _ProjectTableParser(HTMLParser):
    """Parse project report pages for project details."""

    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []
        self.cell_text = ""
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.in_table = True
        if self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        if self.in_row and tag == "td":
            self.in_cell = True
            self.cell_text = ""
        if self.in_row and tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.links.append(href)

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text += data.strip()

    def handle_endtag(self, tag):
        if tag == "td" and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.cell_text)
        if tag == "tr" and self.in_row:
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        if tag == "table":
            self.in_table = False


def _fetch_url(url: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """Fetch URL with retries and rate limiting."""
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=20)
            html = resp.read().decode("utf-8", errors="replace")
            time.sleep(RATE_LIMIT_SECONDS)
            return html
        except Exception as e:
            wait = (attempt + 1) * 5
            logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}. Waiting {wait}s...")
            time.sleep(wait)
    return None


def _fetch_complaint_count(builder_name: str) -> tuple[int, list[dict]]:
    """Fetch complaint count and details for a builder from RERA portal."""
    encoded = urllib.parse.quote(builder_name)
    url = f"{RERA_BASE}/complaintReportWiseList?pName={encoded}"
    html = _fetch_url(url)
    if not html:
        return 0, []

    parser = _ComplaintTableParser()
    parser.feed(html)

    complaints = []
    for row in parser.rows[1:]:
        if len(row) >= 4:
            complaints.append({
                "complaint_no": row[0] if len(row) > 0 else "",
                "project_name": row[1] if len(row) > 1 else "",
                "complainant": row[2] if len(row) > 2 else "",
                "status": row[3] if len(row) > 3 else "",
            })

    return len(complaints), complaints


def _slugify(name: str) -> str:
    """Generate URL slug from builder name."""
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _compute_trust_tier(score: float, has_nclt: bool = False) -> str:
    """Determine trust tier from score with hard overrides."""
    if has_nclt:
        return "avoid"
    if score >= 75:
        return "trusted"
    if score >= 55:
        return "emerging"
    if score >= 40:
        return "cautious"
    return "avoid"


def _normalize_promoter_name(name: str) -> str:
    """Clean up promoter names from RERA complaint data."""
    name = name.strip()
    name = re.sub(r'\s+', ' ', name)
    for suffix in [" Pvt Ltd", " Pvt. Ltd.", " Private Limited", " Pvt.Ltd.",
                   " Ltd.", " Ltd", " Limited", " LLP", " llp"]:
        if name.lower().endswith(suffix.lower()):
            name = name[:len(name) - len(suffix)].strip()
            break
    return name


# ──────────────────────────────────────────────────────────────
# Phase 1: Discovery — find all complained-about promoters
# ──────────────────────────────────────────────────────────────

def discover_builders_from_complaints() -> dict[str, list[dict]]:
    """
    Hit K-RERA complaint list with blank/broad search to discover
    all promoters who have had complaints filed against them.

    Tries multiple approaches:
      1. Blank pName (returns all if portal allows)
      2. Single-char wildcard searches (a, b, c, ...)
      3. Common Bangalore builder name prefixes

    Returns {promoter_name: [complaint_dicts]}.
    """
    print("\n  Phase 1: Discovering builders from RERA complaints...")

    all_complaints: dict[str, list[dict]] = defaultdict(list)

    # Approach 1: Try blank/empty pName
    print("    Trying blank pName search...")
    url = f"{RERA_BASE}/complaintReportWiseList?pName="
    html = _fetch_url(url)
    if html:
        parser = _ComplaintTableParser()
        parser.feed(html)
        rows_found = len(parser.rows) - 1  # minus header
        print(f"    Blank search returned {rows_found} rows")
        if rows_found > 0:
            _extract_promoters_from_rows(parser.rows[1:], all_complaints)

    # Approach 2: If blank didn't return much, try letter-by-letter
    if len(all_complaints) < 20:
        print("    Expanding search with letter prefixes...")
        for letter in "abcdefghijklmnopqrstuvwxyz":
            url = f"{RERA_BASE}/complaintReportWiseList?pName={letter}"
            html = _fetch_url(url)
            if not html:
                continue
            parser = _ComplaintTableParser()
            parser.feed(html)
            rows = parser.rows[1:]
            if rows:
                _extract_promoters_from_rows(rows, all_complaints)
                print(f"    '{letter}': {len(rows)} complaints found")

    # Approach 3: Try common builder prefixes that might yield different results
    common_prefixes = [
        "sri", "shri", "sai", "royal", "prestige", "brigade", "sobha",
        "puravankara", "mantri", "salarpuria", "embassy", "godrej",
        "mahindra", "tata", "birla", "concorde", "shriram", "assetz",
        "vaishnavi", "century", "adarsh", "rohan", "kolte", "mana",
        "dnr", "snn", "provident", "total", "l&t", "ds-max", "sumadhura",
        "nitesh", "karle", "divyasree", "arvind", "pride", "sattva",
        "casa", "fortuna", "vertex", "aparna", "sify", "habitat",
    ]
    existing_names = {n.lower() for n in all_complaints}
    for prefix in common_prefixes:
        if any(prefix in n for n in existing_names):
            continue
        url = f"{RERA_BASE}/complaintReportWiseList?pName={urllib.parse.quote(prefix)}"
        html = _fetch_url(url)
        if not html:
            continue
        parser = _ComplaintTableParser()
        parser.feed(html)
        rows = parser.rows[1:]
        if rows:
            _extract_promoters_from_rows(rows, all_complaints)

    print(f"\n  Discovery complete: {len(all_complaints)} unique promoters found with complaints")
    return dict(all_complaints)


def _extract_promoters_from_rows(rows: list[list[str]], out: dict[str, list[dict]]):
    """Extract promoter names and complaint details from parsed table rows.

    K-RERA complaint table columns vary but typically include:
    complaint_no, project_name, promoter_name, complainant, status
    We try to identify the promoter column heuristically.
    """
    for row in rows:
        if len(row) < 3:
            continue

        complaint = {
            "complaint_no": row[0].strip() if len(row) > 0 else "",
            "project_name": row[1].strip() if len(row) > 1 else "",
            "status": row[-1].strip() if len(row) > 2 else "",
        }

        # The promoter name is typically in column 2 or 3
        # Try to identify it: it's usually a company-like name (contains Pvt/Ltd/LLP/developers/builders/group)
        promoter = ""
        for idx in range(1, min(len(row), 5)):
            cell = row[idx].strip()
            cell_lower = cell.lower()
            if any(kw in cell_lower for kw in [
                "pvt", "ltd", "llp", "developer", "builder", "group",
                "estate", "realty", "properties", "infra", "housing",
                "construction", "homes", "ventures", "projects",
            ]):
                promoter = cell
                break

        if not promoter and len(row) >= 3:
            promoter = row[2].strip()

        if promoter and len(promoter) > 2:
            normalized = _normalize_promoter_name(promoter)
            if normalized:
                out[normalized].append(complaint)


# ──────────────────────────────────────────────────────────────
# Phase 2: Enrichment + DB upsert
# ──────────────────────────────────────────────────────────────

def _enrich_curated_builder(b: dict, complaint_count: int, complaint_details: list[dict]) -> dict:
    """Enrich a curated builder entry with RERA data and trust scores."""
    name = b["name"]
    rera_projects = b.get("rera_projects", 0)
    complaints = complaint_count if complaint_count > 0 else b.get("complaints", 0)
    complaints_ratio = round(complaints / rera_projects, 2) if rera_projects > 0 else 0
    on_time_pct = b.get("on_time_delivery_pct", 70)

    project_names = list(set(
        c["project_name"] for c in complaint_details if c.get("project_name")
    ))

    delivery_score = min(100, on_time_pct * 1.1)
    complaint_penalty = min(50, complaints_ratio * 20)
    legal_score = 100 - complaint_penalty
    satisfaction_score = (b.get("avg_rating", 3.5) / 5.0) * 100

    trust_score = int(
        delivery_score * 0.35
        + legal_score * 0.30
        + satisfaction_score * 0.20
        + 70 * 0.15
    )
    trust_score = max(0, min(100, trust_score))

    return {
        "name": name,
        "slug": _slugify(name),
        "rera_projects": rera_projects,
        "total_projects_blr": b.get("total_projects_blr", 0),
        "complaints": complaints,
        "complaints_ratio": complaints_ratio,
        "on_time_delivery_pct": on_time_pct,
        "avg_rating": b.get("avg_rating"),
        "reputation_tier": b.get("reputation_tier", "established"),
        "active_areas": b.get("active_areas", []),
        "score": b.get("score", trust_score),
        "trust_score": trust_score,
        "trust_tier": _compute_trust_tier(trust_score),
        "trust_score_breakdown": {
            "delivery": round(delivery_score, 1),
            "legal": round(legal_score, 1),
            "satisfaction": round(satisfaction_score, 1),
            "financial": 70,
            "quality": 70,
        },
        "segment": b.get("reputation_tier", "mid-range"),
        "notable_projects": project_names[:5],
        "project_names_from_complaints": project_names,
        "data_source": "curated+rera_scraper",
    }


def _enrich_discovered_builder(name: str, complaints: list[dict]) -> dict:
    """Create a builder entry from discovery data (no curated baseline)."""
    complaint_count = len(complaints)
    project_names = list(set(
        c["project_name"] for c in complaints if c.get("project_name")
    ))

    # With no curated data we only have complaints to work with.
    # High complaints = low trust. Assign conservative defaults.
    complaint_penalty = min(60, complaint_count * 5)
    legal_score = max(10, 100 - complaint_penalty)
    trust_score = int(
        50 * 0.35        # unknown delivery — assume average
        + legal_score * 0.30
        + 50 * 0.20     # unknown satisfaction — assume average
        + 50 * 0.15     # unknown financial — assume average
    )
    trust_score = max(0, min(100, trust_score))

    return {
        "name": name,
        "slug": _slugify(name),
        "rera_projects": 0,
        "total_projects_blr": 0,
        "complaints": complaint_count,
        "complaints_ratio": 0,
        "on_time_delivery_pct": 0,
        "avg_rating": None,
        "reputation_tier": "unknown",
        "active_areas": [],
        "score": trust_score,
        "trust_score": trust_score,
        "trust_tier": _compute_trust_tier(trust_score),
        "trust_score_breakdown": {
            "delivery": 50,
            "legal": round(legal_score, 1),
            "satisfaction": 50,
            "financial": 50,
            "quality": 50,
        },
        "segment": "unknown",
        "notable_projects": project_names[:5],
        "project_names_from_complaints": project_names,
        "data_source": "rera_discovery",
    }


def scrape_all_builders():
    """
    Main scraping pipeline:
    1. Discover all complained-about promoters from RERA
    2. Merge with curated builders.json baseline
    3. Enrich each builder with trust scores
    4. Upsert everything to DB (builders + builder_projects)
    """
    print("=" * 60)
    print("K-RERA Builder & Project Scraper")
    print("=" * 60)

    # Phase 1: Discovery
    discovered = discover_builders_from_complaints()

    # Load curated baseline
    with open(CURATED_DIR / "builders.json") as f:
        curated = json.load(f)

    curated_names = {b["name"].lower(): b for b in curated["builders"]}
    builders_data = []

    # Phase 2a: Process curated builders (with RERA overlay)
    print("\n  Phase 2: Enriching builders...")
    for b in curated["builders"]:
        name = b["name"]
        print(f"\n  Curated: {name}")

        # Check if discovery already found complaints for this builder
        discovery_complaints = []
        for disc_name, disc_complaints in discovered.items():
            if disc_name.lower() == name.lower() or name.lower() in disc_name.lower() or disc_name.lower() in name.lower():
                discovery_complaints = disc_complaints
                discovered.pop(disc_name, None)
                break

        # Also fetch directly by name (more precise)
        direct_count, direct_details = _fetch_complaint_count(name)
        all_complaints = discovery_complaints + direct_details
        unique_complaints = {c.get("complaint_no", ""): c for c in all_complaints if c.get("complaint_no")}
        complaint_list = list(unique_complaints.values())

        entry = _enrich_curated_builder(b, len(complaint_list), complaint_list)
        builders_data.append(entry)
        print(f"    Complaints: {entry['complaints']} | Trust: {entry['trust_score']} ({entry['trust_tier']})")

    # Phase 2b: Process discovered-only builders (not in curated list)
    for disc_name, disc_complaints in discovered.items():
        if disc_name.lower() in curated_names:
            continue
        if len(disc_complaints) == 0:
            continue

        print(f"\n  Discovered: {disc_name} ({len(disc_complaints)} complaints)")
        entry = _enrich_discovered_builder(disc_name, disc_complaints)
        builders_data.append(entry)
        print(f"    Trust: {entry['trust_score']} ({entry['trust_tier']})")

    # Phase 3: Upsert to DB
    _upsert_to_db(builders_data)

    print(f"\n{'=' * 60}")
    curated_count = len(curated["builders"])
    discovered_count = len(builders_data) - curated_count
    print(f"Scraping complete: {len(builders_data)} builders total")
    print(f"  Curated: {curated_count} | Discovered: {discovered_count}")
    by_tier = defaultdict(int)
    for b in builders_data:
        by_tier[b["trust_tier"]] += 1
    for tier in ["trusted", "emerging", "cautious", "avoid"]:
        print(f"  {tier}: {by_tier.get(tier, 0)}")
    print(f"{'=' * 60}")

    return builders_data


def _upsert_to_db(builders: list[dict]):
    """Upsert all builder data to the enhanced builders table + builder_projects."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            projects_seeded = 0

            for b in builders:
                # Upsert base builder row
                cur.execute(
                    """INSERT INTO builders
                       (name, rera_projects, total_projects_blr, complaints, complaints_ratio,
                        on_time_delivery_pct, avg_rating, reputation_tier, active_areas, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (name) DO UPDATE SET
                         complaints = EXCLUDED.complaints,
                         complaints_ratio = EXCLUDED.complaints_ratio,
                         score = EXCLUDED.score,
                         rera_projects = EXCLUDED.rera_projects""",
                    (
                        b["name"], b["rera_projects"], b["total_projects_blr"],
                        b["complaints"], b["complaints_ratio"],
                        b["on_time_delivery_pct"], b["avg_rating"],
                        b["reputation_tier"], b["active_areas"], b["score"],
                    ),
                )

                # Update enhanced columns (from migration 006)
                cur.execute(
                    """UPDATE builders SET
                         slug = %s,
                         trust_score = %s,
                         trust_tier = %s,
                         trust_score_breakdown = %s,
                         segment = %s,
                         notable_projects = %s,
                         data_source = %s,
                         data_last_refreshed = now()
                       WHERE name = %s""",
                    (
                        b["slug"],
                        b["trust_score"],
                        b["trust_tier"],
                        json.dumps(b["trust_score_breakdown"]),
                        b["segment"],
                        b.get("notable_projects", []),
                        b["data_source"],
                        b["name"],
                    ),
                )

                # Seed builder_projects from complaint-discovered project names
                project_names = b.get("project_names_from_complaints", [])
                if project_names:
                    cur.execute("SELECT id FROM builders WHERE name = %s", (b["name"],))
                    row = cur.fetchone()
                    if row:
                        builder_id = row[0]
                        for pname in project_names:
                            pname = pname.strip()
                            if not pname or len(pname) < 3:
                                continue
                            cur.execute(
                                """INSERT INTO builder_projects
                                   (builder_id, project_name, slug, status, data_source)
                                   VALUES (%s, %s, %s, 'ongoing', 'rera_complaints')
                                   ON CONFLICT DO NOTHING""",
                                (builder_id, pname, _slugify(pname)),
                            )
                            projects_seeded += 1

        conn.commit()
        print(f"  DB: {len(builders)} builders upserted, {projects_seeded} projects seeded")
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    scrape_all_builders()
