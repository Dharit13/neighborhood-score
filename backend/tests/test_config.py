"""Tests for configuration values."""

import math


def test_score_weights_sum_to_one():
    from app.config import SCORE_WEIGHTS

    total = sum(SCORE_WEIGHTS.values())
    assert math.isclose(total, 1.0, rel_tol=1e-6), f"Weights sum to {total}, expected 1.0"


def test_score_weights_all_positive():
    from app.config import SCORE_WEIGHTS

    for dim, weight in SCORE_WEIGHTS.items():
        assert weight > 0, f"Weight for {dim} is {weight}, expected > 0"


def test_score_weights_has_expected_dimensions():
    from app.config import SCORE_WEIGHTS

    required = {"safety", "walkability", "transit_access", "hospital_access", "school_access"}
    assert required.issubset(set(SCORE_WEIGHTS.keys()))


def test_bangalore_center_in_range():
    from app.config import BANGALORE_CENTER

    lat, lon = BANGALORE_CENTER
    assert 12.5 < lat < 13.5
    assert 77.0 < lon < 78.2


def test_bangalore_bbox_valid():
    from app.config import BANGALORE_BBOX

    assert BANGALORE_BBOX["south"] < BANGALORE_BBOX["north"]
    assert BANGALORE_BBOX["west"] < BANGALORE_BBOX["east"]
