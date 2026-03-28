"""Tests for utility geo functions (pure, no DB/API calls)."""

import math

from app.utils.geo import (
    count_within_radius,
    decay_score,
    find_nearest,
    haversine_km,
    marketing_walk_claim,
    walk_minutes,
)

# ── haversine_km ──────────────────────────────────────────────


def test_haversine_same_point():
    assert haversine_km(12.97, 77.59, 12.97, 77.59) == 0.0


def test_haversine_known_distance():
    # Indiranagar to Koramangala ≈ 3.5–4.5 km
    dist = haversine_km(12.9784, 77.6408, 12.9352, 77.6245)
    assert 3.0 < dist < 6.0


def test_haversine_symmetry():
    d1 = haversine_km(12.97, 77.59, 13.00, 77.60)
    d2 = haversine_km(13.00, 77.60, 12.97, 77.59)
    assert math.isclose(d1, d2, rel_tol=1e-9)


def test_haversine_positive():
    dist = haversine_km(12.9, 77.5, 13.0, 77.6)
    assert dist > 0


# ── walk_minutes ──────────────────────────────────────────────


def test_walk_minutes_1km():
    assert walk_minutes(1.0) == 12.0  # 1 km at 5 km/h = 12 min


def test_walk_minutes_zero():
    assert walk_minutes(0.0) == 0.0


def test_walk_minutes_custom_speed():
    assert walk_minutes(3.0, speed_kmh=3.0) == 60.0


# ── decay_score ───────────────────────────────────────────────


def test_decay_within_full():
    assert decay_score(0.3, full_score_km=0.5, zero_score_km=2.0) == 1.0


def test_decay_at_full_boundary():
    assert decay_score(0.5, full_score_km=0.5, zero_score_km=2.0) == 1.0


def test_decay_beyond_zero():
    assert decay_score(3.0, full_score_km=0.5, zero_score_km=2.0) == 0.0


def test_decay_at_zero_boundary():
    assert decay_score(2.0, full_score_km=0.5, zero_score_km=2.0) == 0.0


def test_decay_midpoint():
    score = decay_score(1.25, full_score_km=0.5, zero_score_km=2.0)
    assert math.isclose(score, 0.5, rel_tol=1e-9)


def test_decay_returns_between_0_and_1():
    for d in [0.0, 0.5, 1.0, 1.5, 2.0, 5.0]:
        assert 0.0 <= decay_score(d) <= 1.0


# ── find_nearest ──────────────────────────────────────────────


def test_find_nearest_returns_sorted():
    points = [
        {"latitude": 13.0, "longitude": 77.6, "name": "far"},
        {"latitude": 12.971, "longitude": 77.591, "name": "close"},
        {"latitude": 12.98, "longitude": 77.60, "name": "mid"},
    ]
    result = find_nearest(12.97, 77.59, points, top_n=3)
    assert result[0]["name"] == "close"
    assert result[-1]["name"] == "far"
    assert all("distance_km" in r for r in result)


def test_find_nearest_top_n():
    points = [{"latitude": 12.97 + i * 0.01, "longitude": 77.59, "name": f"p{i}"} for i in range(10)]
    result = find_nearest(12.97, 77.59, points, top_n=3)
    assert len(result) == 3


def test_find_nearest_empty():
    assert find_nearest(12.97, 77.59, [], top_n=5) == []


# ── count_within_radius ──────────────────────────────────────


def test_count_within_radius():
    points = [
        {"latitude": 12.971, "longitude": 77.591},  # very close
        {"latitude": 12.98, "longitude": 77.60},  # ~1-2 km
        {"latitude": 13.10, "longitude": 77.70},  # far
    ]
    # 0.5 km radius should only catch the very close point
    assert count_within_radius(12.97, 77.59, points, radius_km=0.5) >= 1
    # 50 km should catch all
    assert count_within_radius(12.97, 77.59, points, radius_km=50.0) == 3


def test_count_within_radius_empty():
    assert count_within_radius(12.97, 77.59, [], radius_km=1.0) == 0


# ── marketing_walk_claim ─────────────────────────────────────


def test_marketing_walk_claim():
    # 1 km at 6 km/h = 10 min
    assert marketing_walk_claim(1.0) == 10.0


def test_marketing_walk_claim_zero():
    assert marketing_walk_claim(0.0) == 0.0
