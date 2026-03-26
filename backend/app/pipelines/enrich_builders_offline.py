"""
Enrich builders in DB with trust scores computed from existing curated data.

No API calls needed -- computes trust_score, trust_tier, slug, segment,
trust_score_breakdown from the fields already in builders.json
(score, complaints, on_time_delivery_pct, avg_rating, etc.)

Usage: python -m app.pipelines.enrich_builders_offline
"""

import json
import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn
from app.config import CURATED_DIR


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _compute_trust_score(b: dict) -> tuple[int, dict]:
    """Compute trust score and breakdown from curated builder fields."""
    on_time_pct = b.get("on_time_delivery_pct", 70)
    complaints = b.get("complaints", 0)
    rera_projects = b.get("rera_projects", 1)
    complaints_ratio = complaints / max(rera_projects, 1)
    avg_rating = b.get("avg_rating", 3.5)

    delivery_score = min(100, on_time_pct * 1.1)
    complaint_penalty = min(50, complaints_ratio * 20)
    legal_score = 100 - complaint_penalty

    if b.get("has_nclt_proceedings"):
        legal_score = max(0, legal_score - 40)

    satisfaction_score = (avg_rating / 5.0) * 100 if avg_rating else 50

    financial_score = 70
    if b.get("has_nclt_proceedings"):
        financial_score = 20
    elif complaints > 20:
        financial_score = 40

    quality_score = 70

    trust_score = int(
        delivery_score * 0.35
        + legal_score * 0.30
        + satisfaction_score * 0.20
        + financial_score * 0.10
        + quality_score * 0.05
    )
    trust_score = max(0, min(100, trust_score))

    breakdown = {
        "delivery": round(delivery_score, 1),
        "legal": round(legal_score, 1),
        "satisfaction": round(satisfaction_score, 1),
        "financial": round(financial_score, 1),
        "quality": round(quality_score, 1),
    }

    return trust_score, breakdown


def _compute_trust_tier(score: int, has_nclt: bool = False) -> str:
    if has_nclt:
        return "avoid"
    if score >= 75:
        return "trusted"
    if score >= 55:
        return "emerging"
    if score >= 40:
        return "cautious"
    return "avoid"


def enrich():
    with open(CURATED_DIR / "builders.json") as f:
        data = json.load(f)

    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            enriched = 0
            for b in data["builders"]:
                name = b["name"]
                slug = _slugify(name)
                has_nclt = b.get("has_nclt_proceedings", False)
                trust_score, breakdown = _compute_trust_score(b)
                trust_tier = _compute_trust_tier(trust_score, has_nclt)
                segment = b.get("reputation_tier", b.get("segment", "mid-range"))

                notable = b.get("notable_projects", [])
                description = b.get("description")
                common_complaints = b.get("common_complaints", [])
                common_praise = b.get("common_praise", [])

                # Upsert base row first
                cur.execute(
                    """INSERT INTO builders
                       (name, rera_projects, total_projects_blr, complaints, complaints_ratio,
                        on_time_delivery_pct, avg_rating, reputation_tier, active_areas, score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (name) DO UPDATE SET
                         complaints = EXCLUDED.complaints,
                         complaints_ratio = EXCLUDED.complaints_ratio,
                         score = EXCLUDED.score,
                         rera_projects = EXCLUDED.rera_projects,
                         on_time_delivery_pct = EXCLUDED.on_time_delivery_pct,
                         avg_rating = EXCLUDED.avg_rating,
                         active_areas = EXCLUDED.active_areas""",
                    (
                        name, b.get("rera_projects", 0), b.get("total_projects_blr", 0),
                        b.get("complaints", 0), b.get("complaints_ratio", 0),
                        b.get("on_time_delivery_pct", 0), b.get("avg_rating"),
                        segment, b.get("active_areas", []), b.get("score", trust_score),
                    ),
                )

                # Update enriched columns
                cur.execute(
                    """UPDATE builders SET
                         slug = %s,
                         trust_score = %s,
                         trust_tier = %s,
                         trust_score_breakdown = %s,
                         segment = %s,
                         notable_projects = %s,
                         description = %s,
                         has_nclt_proceedings = %s,
                         nclt_case_details = %s,
                         common_complaints = %s,
                         common_praise = %s,
                         data_source = %s,
                         data_last_refreshed = now()
                       WHERE name = %s""",
                    (
                        slug,
                        trust_score,
                        trust_tier,
                        json.dumps(breakdown),
                        segment,
                        notable,
                        description,
                        has_nclt,
                        b.get("nclt_case_details"),
                        common_complaints,
                        common_praise,
                        b.get("data_source", "curated"),
                        name,
                    ),
                )
                enriched += 1

                tier_icon = {"trusted": "+", "emerging": "~", "cautious": "!", "avoid": "X"}.get(trust_tier, "?")
                print(f"  [{tier_icon}] {name}: {trust_score} ({trust_tier})")

        conn.commit()
        print(f"\n  OK: {enriched} builders enriched with trust scores")
        return enriched
    finally:
        conn.close()


if __name__ == "__main__":
    enrich()
