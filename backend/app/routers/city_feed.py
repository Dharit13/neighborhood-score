"""City feed endpoints — weather and news for the user's selected city."""

import logging
import time
from difflib import SequenceMatcher

import feedparser
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["city-feed"])

# ---------------------------------------------------------------------------
# In-memory cache: {city_lower: (timestamp, data)}
# ---------------------------------------------------------------------------
CACHE_TTL = 900  # 15 minutes

_weather_cache: dict[str, tuple[float, dict]] = {}
_news_cache: dict[str, tuple[float, dict]] = {}


def _cache_get(cache: dict, key: str) -> dict | None:
    entry = cache.get(key)
    if entry and (time.monotonic() - entry[0]) < CACHE_TTL:
        return entry[1]
    return None


def _cache_set(cache: dict, key: str, data: dict) -> None:
    cache[key] = (time.monotonic(), data)


# ---------------------------------------------------------------------------
# Weather (Open-Meteo — free, no API key)
# ---------------------------------------------------------------------------

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@router.get("/weather")
async def get_weather(city: str = Query(..., min_length=1), _user: dict = Depends(require_auth)):
    cache_key = city.lower()
    cached = _cache_get(_weather_cache, cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=10) as client:
        # Step 1: Geocode city name to lat/lon
        geo_resp = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        geo_resp.raise_for_status()
        geo_data = geo_resp.json()

        results = geo_data.get("results")
        if not results:
            raise HTTPException(status_code=404, detail=f"City not found: {city}")

        lat = results[0]["latitude"]
        lon = results[0]["longitude"]

        # Step 2: Fetch current weather + 5-day forecast
        forecast_resp = await client.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                "timezone": "auto",
                "forecast_days": 5,
            },
        )
        forecast_resp.raise_for_status()
        forecast = forecast_resp.json()

    current = forecast["current"]
    daily = forecast["daily"]

    response = {
        "city": city,
        "current": {
            "temperature": current["temperature_2m"],
            "apparent_temperature": current["apparent_temperature"],
            "humidity": current["relative_humidity_2m"],
            "wind_speed": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
        },
        "daily": [
            {
                "date": daily["time"][i],
                "weather_code": daily["weather_code"][i],
                "temp_max": daily["temperature_2m_max"][i],
                "temp_min": daily["temperature_2m_min"][i],
            }
            for i in range(len(daily["time"]))
        ],
    }

    _cache_set(_weather_cache, cache_key, response)
    return response


# ---------------------------------------------------------------------------
# News (RSS feeds — free, no API key)
# ---------------------------------------------------------------------------

RSS_FEEDS: dict[str, list[str]] = {
    "bengaluru": [
        "https://news.google.com/rss/search?q=Bengaluru&hl=en-IN&gl=IN&ceid=IN:en",
        "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms",
        "https://www.deccanherald.com/bengaluru/rss",
    ],
}


# Fallback: Google News RSS for any city
def _get_feeds(city: str) -> list[str]:
    feeds = RSS_FEEDS.get(city.lower(), [])
    if not feeds:
        feeds = [f"https://news.google.com/rss/search?q={city}&hl=en-IN&gl=IN&ceid=IN:en"]
    return feeds


def _deduplicate(articles: list[dict], threshold: float = 0.75) -> list[dict]:
    """Remove near-duplicate articles by title similarity."""
    unique: list[dict] = []
    for article in articles:
        is_dup = False
        for existing in unique:
            ratio = SequenceMatcher(None, article["title"].lower(), existing["title"].lower()).ratio()
            if ratio >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(article)
    return unique


@router.get("/news")
async def get_news(city: str = Query(..., min_length=1), _user: dict = Depends(require_auth)):
    cache_key = city.lower()
    cached = _cache_get(_news_cache, cache_key)
    if cached:
        return cached

    feeds = _get_feeds(city)
    all_articles: list[dict] = []

    async with httpx.AsyncClient(timeout=10) as client:
        for feed_url in feeds:
            try:
                resp = await client.get(feed_url, follow_redirects=True)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries:
                    source = ""
                    if hasattr(entry, "source") and hasattr(entry.source, "title"):
                        source = entry.source.title
                    elif parsed.feed.get("title"):
                        source = parsed.feed.title

                    thumbnail = ""
                    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                        thumbnail = entry.media_thumbnail[0].get("url", "")
                    elif hasattr(entry, "media_content") and entry.media_content:
                        thumbnail = entry.media_content[0].get("url", "")

                    all_articles.append(
                        {
                            "title": entry.get("title", ""),
                            "source": source,
                            "published": entry.get("published", ""),
                            "link": entry.get("link", ""),
                            "thumbnail": thumbnail,
                        }
                    )
            except Exception:
                logger.warning("Failed to fetch RSS feed: %s", feed_url, exc_info=True)
                continue

    # Sort by published date (newest first), deduplicate, take top 8
    all_articles.sort(key=lambda a: a["published"], reverse=True)
    articles = _deduplicate(all_articles)[:8]

    response = {"city": city, "articles": articles}
    _cache_set(_news_cache, cache_key, response)
    return response
