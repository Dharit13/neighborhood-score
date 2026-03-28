"""
Fetch builder reviews and compute sentiment analysis.

Pipeline:
  1. Google Places API — search builder offices/sales offices for star ratings
  2. Claude sentiment analysis — analyze review themes for each builder
  3. Update builders table with review data

Google Places API is already integrated (fetch_google_places.py).
This pipeline specifically targets builder company reviews.
"""

import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.db import get_sync_conn

logger = logging.getLogger(__name__)

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


def _google_places_rating(builder_name: str) -> dict | None:
    """Search Google Places for builder's office and get rating."""
    if not GOOGLE_MAPS_API_KEY:
        return None

    try:
        import httpx

        query = f"{builder_name} real estate office Bangalore"
        resp = httpx.get(
            "https://maps.googleapis.com/maps/api/place/textsearch/json",
            params={
                "query": query,
                "key": GOOGLE_MAPS_API_KEY,
                "location": "12.97,77.59",
                "radius": "50000",
            },
            timeout=10.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("results"):
                place = data["results"][0]
                return {
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "place_name": place.get("name", ""),
                }
    except Exception as e:
        logger.warning(f"Google Places failed for {builder_name}: {e}")

    return None


def _claude_sentiment_analysis(builder_name: str, rating: float, complaints: int, rera_projects: int) -> dict | None:
    """Use Claude to generate sentiment analysis based on available data."""
    if not ANTHROPIC_API_KEY:
        return None

    try:
        import httpx

        prompt = f"""Analyze the reputation of the Bangalore real estate builder "{builder_name}" based on these data points:
- Google rating: {rating}/5
- RERA registered projects: {rera_projects}
- RERA complaints filed: {complaints}
- Complaints per project ratio: {round(complaints / max(rera_projects, 1), 2)}

Based on your knowledge of this builder and these metrics, provide:
1. A sentiment score from 0.0 (very negative) to 1.0 (very positive)
2. Top 3 common complaints buyers have about this builder
3. Top 3 things buyers praise about this builder

Respond in JSON:
{{"sentiment_score": 0.7, "common_complaints": ["complaint1", "complaint2", "complaint3"], "common_praise": ["praise1", "praise2", "praise3"]}}

If you don't know enough about this builder, base it on the metrics provided.
ONLY output JSON, no explanation."""

        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": ANTHROPIC_MODEL,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=20.0,
        )

        if resp.status_code == 200:
            data = resp.json()
            text = data["content"][0]["text"].strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())

    except Exception as e:
        logger.warning(f"Claude sentiment analysis failed for {builder_name}: {e}")

    return None


def fetch_reviews():
    """Fetch Google Places ratings and run Claude sentiment for all builders."""
    conn = get_sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, avg_rating, complaints, rera_projects FROM builders ORDER BY name")
            builders = cur.fetchall()

            updated = 0
            for builder_id, name, existing_rating, complaints, rera_projects in builders:
                print(f"  Processing: {name}")

                # 1. Get Google Places rating
                places_data = _google_places_rating(name)
                if places_data and places_data.get("rating"):
                    google_rating = places_data["rating"]
                    google_count = places_data["user_ratings_total"]
                    print(f"    Google: {google_rating}/5 ({google_count} reviews)")
                else:
                    google_rating = existing_rating or 3.5
                    google_count = 0
                    print(f"    Google: no results, using existing {google_rating}")

                time.sleep(0.5)

                # 2. Claude sentiment analysis
                sentiment = _claude_sentiment_analysis(name, google_rating or 3.5, complaints or 0, rera_projects or 0)
                if sentiment:
                    sentiment_score = sentiment.get("sentiment_score", 0.5)
                    common_complaints = sentiment.get("common_complaints", [])[:5]
                    common_praise = sentiment.get("common_praise", [])[:5]
                    print(f"    Sentiment: {sentiment_score}")
                else:
                    sentiment_score = None
                    common_complaints = []
                    common_praise = []

                time.sleep(1)

                # 3. Update database
                cur.execute(
                    """UPDATE builders SET
                         avg_rating = COALESCE(%s, avg_rating),
                         review_sentiment_score = %s,
                         common_complaints = %s,
                         common_praise = %s,
                         data_last_refreshed = now()
                       WHERE id = %s""",
                    (
                        google_rating if google_count > 0 else None,
                        sentiment_score,
                        common_complaints,
                        common_praise,
                        builder_id,
                    ),
                )
                updated += 1

        conn.commit()
        print(f"\n  Reviews processed: {updated} builders")
        return updated
    finally:
        conn.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    fetch_reviews()
