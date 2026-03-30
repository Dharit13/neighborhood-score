from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LocationInput(BaseModel):
    latitude: float | None = Field(None, ge=12.5, le=13.5, description="Latitude (Bangalore range)")
    longitude: float | None = Field(None, ge=77.0, le=78.2, description="Longitude (Bangalore range)")
    address: str | None = Field(None, description="Address or area name in Bangalore")
    builder_name: str | None = Field(None, description="Builder name for reputation score")


class NearbyDetail(BaseModel):
    name: str
    distance_km: float
    category: str
    latitude: float
    longitude: float


class ScoreResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    label: str
    data_confidence: str | None = None
    details: list[NearbyDetail] = []
    breakdown: dict[str, Any] = {}
    sources: list[str] = []


class TransitDetail(BaseModel):
    name: str
    type: str
    distance_km: float
    walk_minutes: float
    actual_walk_km: float | None = None
    marketing_claim_minutes: float | None = None
    straight_line_km: float | None = None
    drive_km: float | None = None
    drive_offpeak_minutes: float | None = None
    drive_peak_minutes: float | None = None
    recommended_mode: str | None = None
    latitude: float
    longitude: float


class TransitScoreResult(ScoreResult):
    nearest_bus_stop: TransitDetail | None = None
    nearest_metro: TransitDetail | None = None
    nearest_train: TransitDetail | None = None
    airport: TransitDetail | None = None
    majestic: TransitDetail | None = None
    city_railway: TransitDetail | None = None
    peak_travel_time_min: float | None = None
    offpeak_travel_time_min: float | None = None


class BuilderDetail(BaseModel):
    name: str
    score: float
    rera_projects: int
    complaints: int
    complaints_ratio: float
    delivery_rating: str
    active_in_area: bool = False
    avoid_reason: str | None = None


class BuilderScoreResult(ScoreResult):
    builders: list[BuilderDetail] = []
    recommended_builders: list[BuilderDetail] = []
    builders_to_avoid: list[BuilderDetail] = []


class LifestyleTag(BaseModel):
    category: str = ""
    label: str = ""
    detail: str = ""


class AIVerification(BaseModel):
    confidence: int = Field(..., ge=0, le=100)
    narrative: str = ""
    verdict: str = ""
    pros: list[str] = []
    cons: list[str] = []
    best_for: str = ""
    avoid_if: str = ""
    flags: list[str] = []
    lifestyle_tags: list[LifestyleTag] = []
    verified_at: datetime | None = None
    model_used: str | None = None


class NeighborhoodRank(BaseModel):
    name: str
    score: float
    label: str
    highlights: list[str] = []


class RentVsBuyArea(BaseModel):
    area: str
    recommendation: str
    avg_2bhk_rent: int
    monthly_emi: int
    emi_rent_ratio: float
    rental_yield_pct: float
    avg_price_sqft: int


class WardInfo(BaseModel):
    name: str
    corporation: str
    population: int | None = None
    distance_km: float | None = None


class NeighborhoodScoreResponse(BaseModel):
    latitude: float
    longitude: float
    address: str
    composite_score: float
    composite_label: str
    walkability: ScoreResult
    safety: ScoreResult
    hospital_access: ScoreResult
    school_access: ScoreResult
    transit_access: TransitScoreResult
    builder_reputation: BuilderScoreResult
    air_quality: ScoreResult
    water_supply: ScoreResult
    power_reliability: ScoreResult
    future_infrastructure: ScoreResult
    property_prices: ScoreResult
    flood_risk: ScoreResult
    commute: ScoreResult
    delivery_coverage: ScoreResult
    noise: ScoreResult
    business_opportunity: ScoreResult
    cleanliness: ScoreResult
    ai_verification: AIVerification | None = None
    recommended_neighborhoods: list[NeighborhoodRank] = []
    neighborhoods_to_avoid: list[NeighborhoodRank] = []
    best_to_buy: list[RentVsBuyArea] = []
    best_to_rent: list[RentVsBuyArea] = []
    wards_covered: list[WardInfo] = []
    wards_total_population: int | None = None


class ClaimInput(BaseModel):
    latitude: float | None = Field(None, ge=12.5, le=13.5)
    longitude: float | None = Field(None, ge=77.0, le=78.2)
    address: str | None = None
    claims: list[str] = Field(default_factory=list)
    raw_text: str | None = None


class ClaimVerification(BaseModel):
    original_claim: str
    claimed_value: str
    actual_value: str
    difference: str
    verdict: str
    details: dict[str, Any] = {}


class ClaimVerificationResponse(BaseModel):
    latitude: float
    longitude: float
    address: str
    results: list[ClaimVerification]
    summary: str
    narrative: str = ""
    extracted_claims: list[str] = []


class RecommendInput(BaseModel):
    budget_type: str = Field(..., description="'buy' or 'rent'")
    budget_range: str = Field(..., description="e.g. '60L-1Cr', 'Under 60L', '20-35K'")
    commute_destination: str | None = Field(None, description="Where the user commutes to")
    priorities: list[str] = Field(..., description="Top 3 priorities e.g. ['safety','metro_access','schools']")
    lifestyle: str = Field(..., description="e.g. 'young_professional', 'family_with_kids'")


class RecommendItem(BaseModel):
    neighborhood: str
    match_score: int = Field(..., ge=0, le=100)
    reason: str
    highlights: list[str]
    scores: dict[str, Any]


class RecommendResponse(BaseModel):
    recommendations: list[RecommendItem]


def score_label(score: float) -> str:
    if score >= 75:
        return "Top Notch"
    elif score >= 68:
        return "Excellent"
    elif score >= 60:
        return "Very Good"
    elif score >= 52:
        return "Good"
    else:
        return "Avoid"
