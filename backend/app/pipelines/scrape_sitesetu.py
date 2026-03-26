"""
Scrape SiteSetu RERA directory for Bangalore builder projects.

Source: sitesetu.app/rera/karnataka/bangalore
112 RERA-registered projects from 23 developers with structured data.

Populates the builder_projects table by matching developer names
to existing builders in the DB.

Usage: python -m app.pipelines.scrape_sitesetu
"""

import re
import sys
import os
import time
import logging
import urllib.request
from html.parser import HTMLParser
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

logger = logging.getLogger(__name__)

SITESETU_BASE = "https://sitesetu.app"
BANGALORE_URL = f"{SITESETU_BASE}/rera/karnataka/bangalore"
RATE_LIMIT = 1.5
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


class _ProjectLinkParser(HTMLParser):
    """Extract project page links from the listing page."""

    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href.startswith("/rera/karnataka/bangalore/") and href.count("/") == 4:
                if href not in self.links:
                    self.links.append(href)


class _ProjectPageParser(HTMLParser):
    """Extract project details from individual project pages."""

    def __init__(self):
        super().__init__()
        self.in_h1 = False
        self.in_detail_label = False
        self.in_detail_value = False
        self.current_label = ""
        self.project_name = ""
        self.details: dict[str, str] = {}
        self._text_buffer = ""
        self._capture = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.in_h1 = True
            self._text_buffer = ""

    def handle_data(self, data):
        text = data.strip()
        if self.in_h1:
            self._text_buffer += text

        # Capture key-value pairs from project details table
        known_labels = [
            "Project Name", "Developer/Promoter", "Location", "City",
            "Project Type", "Units/Towers", "Expected Completion",
            "RERA Number", "Registration Date",
        ]
        for label in known_labels:
            if text == label:
                self.current_label = label
                self.in_detail_label = True
                return

        if self.current_label and text and text != self.current_label:
            if text not in ("Project Details", "RERA Registration"):
                self.details[self.current_label] = text
                self.current_label = ""

    def handle_endtag(self, tag):
        if tag == "h1" and self.in_h1:
            self.in_h1 = False
            self.project_name = self._text_buffer.strip()


def _fetch_url(url: str) -> Optional[str]:
    """Fetch URL with rate limiting."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")
        time.sleep(RATE_LIMIT)
        return html
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _extract_area(location: str) -> Optional[str]:
    """Extract the primary area name from a SiteSetu location string."""
    if not location:
        return None
    parts = location.split(",")
    return parts[0].strip()


def scrape():
    """Scrape SiteSetu for all Bangalore RERA projects and populate builder_projects."""
    print("=" * 60)
    print("SiteSetu RERA Project Scraper — Bangalore")
    print("=" * 60)

    # Step 1: Get all project links from the listing page
    print("\n  Fetching project listing...")
    html = _fetch_url(BANGALORE_URL)
    if not html:
        print("  ERROR: Could not fetch SiteSetu listing page")
        return 0

    link_parser = _ProjectLinkParser()
    link_parser.feed(html)
    project_links = link_parser.links
    print(f"  Found {len(project_links)} project links on listing page")

    # Step 2: Fetch each project page for details
    projects = []
    for i, link in enumerate(project_links):
        url = f"{SITESETU_BASE}{link}"
        print(f"  [{i+1}/{len(project_links)}] {link.split('/')[-1]}...", end=" ", flush=True)

        html = _fetch_url(url)
        if not html:
            print("SKIP")
            continue

        parser = _ProjectPageParser()
        parser.feed(html)

        project = {
            "project_name": parser.details.get("Project Name", parser.project_name),
            "developer": parser.details.get("Developer/Promoter", ""),
            "location": parser.details.get("Location", ""),
            "project_type": parser.details.get("Project Type", ""),
            "rera_number": parser.details.get("RERA Number", ""),
            "expected_completion": parser.details.get("Expected Completion", ""),
            "units": parser.details.get("Units/Towers", ""),
        }

        if project["project_name"]:
            projects.append(project)
            print(f"OK ({project['developer']})")
        else:
            print("NO DATA")

    print(f"\n  Scraped {len(projects)} projects total")

    # Step 3: Insert into DB
    _insert_projects(projects)

    print(f"\n{'=' * 60}")
    print(f"SiteSetu scrape complete: {len(projects)} projects")
    print(f"{'=' * 60}")

    return len(projects)


def _insert_projects(projects: list[dict]):
    """Match projects to builders and insert into builder_projects table."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            # Build a map of builder names to IDs
            cur.execute("SELECT id, name, slug FROM builders")
            builder_map: dict[str, int] = {}
            for row in cur.fetchall():
                builder_map[row[1].lower()] = row[0]
                if row[2]:
                    builder_map[row[2].lower()] = row[0]

            inserted = 0
            unmatched_devs = set()

            for p in projects:
                dev = p["developer"]
                dev_lower = dev.lower()

                # Try exact match, then partial
                builder_id = builder_map.get(dev_lower)
                if not builder_id:
                    for bname, bid in builder_map.items():
                        if bname in dev_lower or dev_lower in bname:
                            builder_id = bid
                            break

                if not builder_id:
                    # Insert the developer as a new builder if not found
                    unmatched_devs.add(dev)
                    cur.execute(
                        """INSERT INTO builders (name, rera_projects, score, reputation_tier, slug)
                           VALUES (%s, 1, 60, 'emerging', %s)
                           ON CONFLICT (name) DO NOTHING
                           RETURNING id""",
                        (dev, _slugify(dev)),
                    )
                    result = cur.fetchone()
                    if result:
                        builder_id = result[0]
                        builder_map[dev_lower] = builder_id
                    else:
                        cur.execute("SELECT id FROM builders WHERE name = %s", (dev,))
                        row = cur.fetchone()
                        if row:
                            builder_id = row[0]

                if not builder_id:
                    continue

                area = _extract_area(p["location"])
                slug = _slugify(p["project_name"])

                cur.execute(
                    """INSERT INTO builder_projects
                       (builder_id, project_name, slug, rera_number,
                        location_area, project_type, status, data_source)
                       VALUES (%s, %s, %s, %s, %s, %s, 'ongoing', 'sitesetu')
                       ON CONFLICT DO NOTHING""",
                    (
                        builder_id,
                        p["project_name"],
                        slug,
                        p["rera_number"] or None,
                        area,
                        p["project_type"] or None,
                    ),
                )
                inserted += 1

        conn.commit()
        print(f"\n  DB: {inserted} projects inserted into builder_projects")
        if unmatched_devs:
            print(f"  New developers added: {', '.join(sorted(unmatched_devs))}")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape()
