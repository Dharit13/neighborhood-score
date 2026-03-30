"""Tests for API endpoints (mocked DB — no real connections needed)."""

from unittest.mock import AsyncMock, patch

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


def test_root(client):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Neighbourhood Score"
    assert "version" in data
    assert "methodology" in data


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_map_config(client):
    resp = client.get("/api/config/map")
    assert resp.status_code == 200
    data = resp.json()
    assert "google_maps_api_key" in data
    assert "center" in data
    assert "lat" in data["center"]
    assert "lon" in data["center"]


def test_scores_missing_input(client):
    resp = client.post("/api/scores", json={})
    # Should return 400 or 422 — no lat/lon/address provided
    assert resp.status_code in (400, 422)


def test_scores_invalid_latitude(client):
    resp = client.post("/api/scores", json={"latitude": 28.0, "longitude": 77.5})
    assert resp.status_code == 422


def test_scores_invalid_longitude(client):
    resp = client.post("/api/scores", json={"latitude": 12.97, "longitude": 50.0})
    assert resp.status_code == 422


def test_scores_outside_bangalore_bbox(client):
    """Coordinates within Pydantic range but outside Bangalore bbox should return 400."""
    resp = client.post("/api/scores", json={"latitude": 13.20, "longitude": 77.5})
    assert resp.status_code == 400
    assert "outside Bangalore" in resp.json()["detail"]


def test_scores_inside_bangalore_bbox(client):
    """Valid Bangalore coordinates should not trigger bbox rejection."""
    try:
        resp = client.post("/api/scores", json={"latitude": 12.97, "longitude": 77.59})
    except Exception:
        # Mocked DB may raise; the important thing is we didn't get a bbox 400
        return
    # Should not be 400 (bbox passes); may be 500 due to mocked DB, but not a bbox error
    assert resp.status_code != 400 or "outside Bangalore" not in resp.json().get("detail", "")
