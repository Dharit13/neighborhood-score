from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional


class LocationInput(BaseModel):
    latitude: Optional[float] = Field(None, ge=12.5, le=13.5, description="Latitude (Bangalore range)")
    longitude: Optional[float] = Field(None, ge=77.0, le=78.2, description="Longitude (Bangalore range)")
    address: Optional[str] = Field(None, description="Address or area name in Bangalore")
    builder_name: Optional[str] = Field(None, description="Builder name for reputation score")


class NearbyDetail(BaseModel):
    name: str
    distance_km: float
    category: str
    latitude: float
    longitude: float


class ScoreResult(BaseModel):
    score: float = Field(..., ge=0, le=100)
    label: str
    data_confidence: Optional[str] = None
    details: list[NearbyDetail] = []
    breakdown: dict[str, Any] = {}
    sources: list[str] = []


class TransitDetail(BaseModel):
    name: str
    type: str
    distance_km: float
    walk_minutes: float
    actual_walk_km: Optional[float] = None
    marketing_claim_minutes: Optional[float] = None
    straight_line_km: Optional[float] = None
    drive_km: Optional[float] = None
    drive_offpeak_minutes: Optional[float] = None
    drive_peak_minutes: Optional[float] = None
    recommended_mode: Optional[str] = None
    latitude: float
    longitude: float


class TransitScoreResult(ScoreResult):
    nearest_bus_stop: Optional[TransitDetail] = None
    nearest_metro: Optional[TransitDetail] = None
    nearest_train: Optional[TransitDetail] = None
    airport: Optional[TransitDetail] = None
    majestic: Optional[TransitDetail] = None
    city_railway: Optional[TransitDetail] = None
    peak_travel_time_min: Optional[float] = None
    offpeak_travel_time_min: Optional[float] = None


class BuilderDetail(BaseModel):
    name: str
    score: float
    rera_projects: int
    complaints: int
    complaints_ratio: float
    delivery_rating: str
    active_in_area: bool = False
    avoid_reason: Optional[str] = None


class BuilderScoreResult(ScoreResult):
    builders: list[BuilderDetail] = []
    recommended_builders: list[BuilderDetail] = []
    builders_to_avoid: list[BuilderDetail] = []


class AIVerification(BaseModel):
    confidence: int = Field(..., ge=0, le=100)
    narrative: str = ""
    verdict: str = ""
    pros: list[str] = []
    cons: list[str] = []
    best_for: str = ""
    avoid_if: str = ""
    flags: list[str] = []
    verified_at: Optional[datetime] = None
    model_used: Optional[str] = None


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
    population: Optional[int] = None
    distance_km: Optional[float] = None


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
    ai_verification: Optional[AIVerification] = None
    recommended_neighborhoods: list[NeighborhoodRank] = []
    neighborhoods_to_avoid: list[NeighborhoodRank] = []
    best_to_buy: list[RentVsBuyArea] = []
    best_to_rent: list[RentVsBuyArea] = []
    wards_covered: list[WardInfo] = []
    wards_total_population: Optional[int] = None


class ClaimInput(BaseModel):
    latitude: Optional[float] = Field(None, ge=12.5, le=13.5)
    longitude: Optional[float] = Field(None, ge=77.0, le=78.2)
    address: Optional[str] = None
    claims: list[str] = Field(..., min_length=1)


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


def score_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Very Good"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Average"
    elif score >= 25:
        return "Below Average"
    else:
        return "Poor"
