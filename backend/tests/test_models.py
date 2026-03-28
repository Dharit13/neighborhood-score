"""Tests for Pydantic models and score_label."""

import pytest
from pydantic import ValidationError

from app.models import (
    ClaimInput,
    LocationInput,
    NearbyDetail,
    ScoreResult,
    score_label,
)

# ── score_label ───────────────────────────────────────────────


def test_score_label_top_notch():
    assert score_label(75) == "Top Notch"
    assert score_label(100) == "Top Notch"


def test_score_label_excellent():
    assert score_label(68) == "Excellent"
    assert score_label(74.9) == "Excellent"


def test_score_label_very_good():
    assert score_label(60) == "Very Good"
    assert score_label(67.9) == "Very Good"


def test_score_label_good():
    assert score_label(52) == "Good"
    assert score_label(59.9) == "Good"


def test_score_label_avoid():
    assert score_label(0) == "Avoid"
    assert score_label(51.9) == "Avoid"


# ── ScoreResult validation ───────────────────────────────────


def test_score_result_valid():
    sr = ScoreResult(score=72.5, label="Excellent")
    assert sr.score == 72.5
    assert sr.details == []
    assert sr.sources == []


def test_score_result_bounds():
    with pytest.raises(ValidationError):
        ScoreResult(score=-1, label="Bad")
    with pytest.raises(ValidationError):
        ScoreResult(score=101, label="Over")


def test_score_result_with_details():
    detail = NearbyDetail(name="Hospital", distance_km=0.5, category="health", latitude=12.97, longitude=77.59)
    sr = ScoreResult(score=80, label="Top Notch", details=[detail])
    assert len(sr.details) == 1
    assert sr.details[0].name == "Hospital"


# ── LocationInput validation ─────────────────────────────────


def test_location_input_with_coords():
    loc = LocationInput(latitude=12.97, longitude=77.59)
    assert loc.latitude == 12.97


def test_location_input_with_address():
    loc = LocationInput(address="Indiranagar, Bangalore")
    assert loc.address == "Indiranagar, Bangalore"
    assert loc.latitude is None


def test_location_input_lat_out_of_bangalore_range():
    with pytest.raises(ValidationError):
        LocationInput(latitude=28.0, longitude=77.59)  # Delhi lat


def test_location_input_lon_out_of_bangalore_range():
    with pytest.raises(ValidationError):
        LocationInput(latitude=12.97, longitude=72.0)  # Mumbai lon


def test_location_input_empty_is_valid():
    loc = LocationInput()
    assert loc.latitude is None
    assert loc.address is None


# ── ClaimInput validation ────────────────────────────────────


def test_claim_input_with_claims():
    ci = ClaimInput(latitude=12.97, longitude=77.59, claims=["Near metro"])
    assert len(ci.claims) == 1


def test_claim_input_lat_out_of_range():
    with pytest.raises(ValidationError):
        ClaimInput(latitude=20.0, longitude=77.59)
