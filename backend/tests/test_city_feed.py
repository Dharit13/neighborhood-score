"""Tests for city feed endpoints (weather + news)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


async def _fake_auth():
    return {"sub": "test-user"}


@pytest.fixture
def client():
    """Create a test client with DB pool and auth mocked out."""
    with patch("app.db.get_pool", new_callable=AsyncMock):
        with patch("app.db.close_pool", new_callable=AsyncMock):
            from app.auth import require_auth
            from app.main import app

            app.dependency_overrides[require_auth] = _fake_auth
            with TestClient(app) as c:
                yield c
            app.dependency_overrides.clear()


# --- Weather tests ---

MOCK_GEOCODE_RESPONSE = {
    "results": [
        {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946}
    ]
}

MOCK_FORECAST_RESPONSE = {
    "current": {
        "temperature_2m": 28.5,
        "apparent_temperature": 30.1,
        "relative_humidity_2m": 65,
        "wind_speed_10m": 12.3,
        "weather_code": 1,
    },
    "daily": {
        "time": ["2026-04-02", "2026-04-03", "2026-04-04", "2026-04-05", "2026-04-06"],
        "weather_code": [1, 2, 3, 61, 0],
        "temperature_2m_max": [32, 31, 30, 28, 33],
        "temperature_2m_min": [21, 20, 19, 18, 22],
    },
}


def _mock_httpx_get(url, **kwargs):
    """Return mock responses based on URL."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    if "geocoding-api" in url:
        mock_resp.json.return_value = MOCK_GEOCODE_RESPONSE
    elif "api.open-meteo.com" in url:
        mock_resp.json.return_value = MOCK_FORECAST_RESPONSE
    return mock_resp


@patch("app.routers.city_feed.httpx.AsyncClient")
def test_weather_success(mock_client_cls, client):
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(side_effect=_mock_httpx_get)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_instance

    # Clear cache before test
    from app.routers.city_feed import _weather_cache
    _weather_cache.clear()

    resp = client.get("/api/weather?city=Bengaluru")
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Bengaluru"
    assert data["current"]["temperature"] == 28.5
    assert data["current"]["humidity"] == 65
    assert data["current"]["wind_speed"] == 12.3
    assert data["current"]["weather_code"] == 1
    assert data["current"]["apparent_temperature"] == 30.1
    assert len(data["daily"]) == 5
    assert data["daily"][0]["date"] == "2026-04-02"
    assert data["daily"][0]["temp_max"] == 32
    assert data["daily"][0]["temp_min"] == 21


def test_weather_missing_city(client):
    resp = client.get("/api/weather")
    assert resp.status_code == 422


@patch("app.routers.city_feed.httpx.AsyncClient")
def test_weather_cache_hit(mock_client_cls, client):
    """Second call should use cache — httpx not called again."""
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(side_effect=_mock_httpx_get)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_instance

    from app.routers.city_feed import _weather_cache
    _weather_cache.clear()

    client.get("/api/weather?city=Bengaluru")
    client.get("/api/weather?city=Bengaluru")

    # AsyncClient should only be instantiated once (first call fetches, second uses cache)
    assert mock_client_cls.call_count == 1


# --- News tests ---

MOCK_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Bengaluru metro expansion approved</title>
      <link>https://example.com/article1</link>
      <pubDate>Wed, 02 Apr 2026 10:30:00 GMT</pubDate>
      <source url="https://example.com">Times of India</source>
    </item>
    <item>
      <title>Traffic disruption in Bengaluru CBD</title>
      <link>https://example.com/article2</link>
      <pubDate>Wed, 02 Apr 2026 08:00:00 GMT</pubDate>
      <source url="https://example.com">Deccan Herald</source>
    </item>
  </channel>
</rss>"""


def _mock_httpx_get_rss(_url, **kwargs):
    """Return mock RSS response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = MOCK_RSS_XML
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@patch("app.routers.city_feed.httpx.AsyncClient")
def test_news_success(mock_client_cls, client):
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(side_effect=_mock_httpx_get_rss)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_instance

    from app.routers.city_feed import _news_cache
    _news_cache.clear()

    resp = client.get("/api/news?city=Bengaluru")
    assert resp.status_code == 200
    data = resp.json()
    assert data["city"] == "Bengaluru"
    assert len(data["articles"]) > 0
    article = data["articles"][0]
    assert "title" in article
    assert "link" in article
    assert "source" in article
    assert "published" in article


def test_news_missing_city(client):
    resp = client.get("/api/news")
    assert resp.status_code == 422


@patch("app.routers.city_feed.httpx.AsyncClient")
def test_news_cache_hit(mock_client_cls, client):
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(side_effect=_mock_httpx_get_rss)
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_cls.return_value = mock_instance

    from app.routers.city_feed import _news_cache
    _news_cache.clear()

    client.get("/api/news?city=Bengaluru")
    client.get("/api/news?city=Bengaluru")

    assert mock_client_cls.call_count == 1
