"""
Compute 5-dimension trust scores for all builders.

Dimensions and weights:
  1. Delivery reliability: 30% — on-time ratio from RERA data
  2. Legal safety: 25% — inverted penalty from complaints + NCLT
  3. Financial health: 20% — company status, director risk, charges
  4. Customer satisfaction: 15% — normalized review score
  5. Construction quality: 10% — keyword analysis on complaints/praise

Hard overrides:
  - NCLT proceedings → "avoid" tier regardless of score
  - Non-active company status → "avoid"
  - Directors linked to failed companies AND score < 60 → "cautious" minimum

Tier mapping:
  75-100 → "trusted" (green)
  55-74  → "emerging" (blue)
  40-54  → "cautious" (yellow)
  0-39   → "avoid" (red)
"""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

logger = logging.getLogger(__name__)

WEIGHTS = {
    "delivery": 0.30,
    "legal": 0.25,
    "financial": 0.20,
    "satisfaction": 0.15,
    "quality": 0.10,
}

QUALITY_NEGATIVE_KEYWORDS = [
    "water leakage",
    "seepage",
    "cracks",
    "poor quality",
    "construction defect",
    "finishing",
    "low quality",
    "cheap material",
    "waterproofing",
    "structural",
    "plumbing",
    "electrical issues",
]

QUALITY_POSITIVE_KEYWORDS = [
    "excellent quality",
    "good construction",
    "solid build",
    "well built",
    "premium material",
    "superior finish",
    "earthquake resistant",
    "green building",
    "igbc",
    "leed",
    "iso certified",
]


def compute_delivery_score(builder: dict) -> float:
    """Score based on on-time delivery percentage."""
    on_time_pct = builder.get("on_time_delivery_pct", 0) or 0

    if on_time_pct >= 90:
        return 95
    elif on_time_pct >= 80:
        return 80
    elif on_time_pct >= 70:
        return 65
    elif on_time_pct >= 60:
        return 50
    elif on_time_pct >= 50:
        return 35
    else:
        return 20

    return max(0, min(100, on_time_pct * 1.1))


def compute_legal_score(builder: dict) -> float:
    """Score based on legal risk — complaints, NCLT, consumer court."""
    score = 100.0

    complaints_ratio = builder.get("complaints_ratio", 0) or 0
    if complaints_ratio > 3.0:
        score -= 50
    elif complaints_ratio > 2.0:
        score -= 35
    elif complaints_ratio > 1.5:
        score -= 25
    elif complaints_ratio > 1.0:
        score -= 15
    elif complaints_ratio > 0.5:
        score -= 5

    complaints = builder.get("complaints", 0) or 0
    if complaints > 20:
        score -= 20
    elif complaints > 15:
        score -= 10
    elif complaints > 10:
        score -= 5

    if builder.get("has_nclt_proceedings"):
        score = min(score, 10)

    consumer_court = builder.get("consumer_court_cases", 0) or 0
    if consumer_court >= 10:
        score -= 25
    elif consumer_court >= 5:
        score -= 15

    return max(0, min(100, score))


def compute_financial_score(builder: dict) -> float:
    """Score based on financial health indicators."""
    score = 70.0  # Default for unknown

    status = (builder.get("company_status") or "").lower()
    if status in ("active", ""):
        score = 75.0
    elif status in ("under process of striking off", "dormant"):
        score = 30.0
    elif status in ("struck off", "liquidated", "under liquidation"):
        score = 5.0

    if builder.get("directors_linked_to_failed"):
        score -= 25

    charges = builder.get("charges_registered", 0) or 0
    if charges > 50:
        score -= 15
    elif charges > 20:
        score -= 5

    trend = (builder.get("profit_loss_trend") or "").lower()
    if trend == "growing":
        score += 10
    elif trend == "declining":
        score -= 10

    return max(0, min(100, score))


def compute_satisfaction_score(builder: dict) -> float:
    """Score based on customer reviews and ratings."""
    rating = builder.get("avg_rating")
    if not rating:
        return 60.0  # Default for no reviews

    # Normalize 1-5 rating to 0-100 scale
    if rating >= 4.5:
        return 95
    elif rating >= 4.0:
        return 80
    elif rating >= 3.5:
        return 65
    elif rating >= 3.0:
        return 50
    elif rating >= 2.5:
        return 35
    else:
        return 20


def compute_quality_score(builder: dict) -> float:
    """Score based on keyword analysis of complaints and praise."""
    score = 65.0  # Default

    complaints_text = " ".join(builder.get("common_complaints", []) or []).lower()
    praise_text = " ".join(builder.get("common_praise", []) or []).lower()

    for keyword in QUALITY_NEGATIVE_KEYWORDS:
        if keyword in complaints_text:
            score -= 5

    for keyword in QUALITY_POSITIVE_KEYWORDS:
        if keyword in praise_text:
            score += 5

    # Certifications boost
    certs = builder.get("certifications", []) or []
    cert_text = " ".join(certs).lower()
    if "igbc" in cert_text or "leed" in cert_text:
        score += 10
    if "iso" in cert_text:
        score += 5

    return max(0, min(100, score))


def compute_trust_score(builder: dict) -> dict:
    """
    Compute composite trust score with breakdown.
    Returns dict with score, tier, and per-dimension breakdown.
    """
    delivery = compute_delivery_score(builder)
    legal = compute_legal_score(builder)
    financial = compute_financial_score(builder)
    satisfaction = compute_satisfaction_score(builder)
    quality = compute_quality_score(builder)

    composite = (
        delivery * WEIGHTS["delivery"]
        + legal * WEIGHTS["legal"]
        + financial * WEIGHTS["financial"]
        + satisfaction * WEIGHTS["satisfaction"]
        + quality * WEIGHTS["quality"]
    )
    composite = round(max(0, min(100, composite)))

    # Hard overrides
    has_nclt = builder.get("has_nclt_proceedings", False)
    status = (builder.get("company_status") or "").lower()
    is_inactive = status in ("struck off", "liquidated", "under liquidation", "dormant")
    directors_risky = builder.get("directors_linked_to_failed", False)

    if has_nclt or is_inactive:
        tier = "avoid"
        if composite > 39:
            composite = min(composite, 35)
    elif directors_risky and composite < 60:
        tier = "cautious"
    elif composite >= 75:
        tier = "trusted"
    elif composite >= 55:
        tier = "emerging"
    elif composite >= 40:
        tier = "cautious"
    else:
        tier = "avoid"

    return {
        "trust_score": composite,
        "trust_tier": tier,
        "breakdown": {
            "delivery": round(delivery, 1),
            "legal": round(legal, 1),
            "financial": round(financial, 1),
            "satisfaction": round(satisfaction, 1),
            "quality": round(quality, 1),
        },
        "overrides_applied": [
            o
            for o in [
                "nclt_override" if has_nclt else None,
                "inactive_company_override" if is_inactive else None,
                "director_risk_override" if (directors_risky and composite < 60) else None,
            ]
            if o
        ],
    }


def compute_all():
    """Compute trust scores for all builders in the database."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, rera_projects, complaints, complaints_ratio,
                          on_time_delivery_pct, avg_rating, reputation_tier,
                          has_nclt_proceedings, company_status,
                          directors_linked_to_failed, charges_registered,
                          profit_loss_trend, consumer_court_cases,
                          common_complaints, common_praise, certifications
                   FROM builders"""
            )
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            updated = 0
            for row in rows:
                builder = dict(zip(columns, row))
                result = compute_trust_score(builder)

                cur.execute(
                    """UPDATE builders SET
                         trust_score = %s,
                         trust_tier = %s,
                         trust_score_breakdown = %s
                       WHERE id = %s""",
                    (
                        result["trust_score"],
                        result["trust_tier"],
                        json.dumps(result["breakdown"]),
                        builder["id"],
                    ),
                )
                updated += 1
                print(f"  {builder['name']}: {result['trust_score']} ({result['trust_tier']})")
                if result["overrides_applied"]:
                    print(f"    Overrides: {', '.join(result['overrides_applied'])}")

        conn.commit()
        print(f"\n  OK: {updated} builders scored")
        return updated
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    compute_all()
