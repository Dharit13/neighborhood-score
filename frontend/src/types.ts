export interface NearbyDetail {
  name: string;
  distance_km: number;
  category: string;
  latitude: number;
  longitude: number;
}

export interface ScoreResult {
  score: number;
  label: string;
  data_confidence?: string | null;
  details: NearbyDetail[];
  breakdown: Record<string, unknown>;
  sources: string[];
}

export interface TransitDetail {
  name: string;
  type: string;
  distance_km: number;
  walk_minutes: number;
  actual_walk_km?: number;
  marketing_claim_minutes?: number;
  straight_line_km?: number;
  drive_km?: number;
  drive_offpeak_minutes?: number;
  drive_peak_minutes?: number;
  recommended_mode?: string;
  latitude: number;
  longitude: number;
}

export interface TransitScoreResult extends ScoreResult {
  nearest_bus_stop: TransitDetail | null;
  nearest_metro: TransitDetail | null;
  nearest_train: TransitDetail | null;
  airport: TransitDetail | null;
  majestic: TransitDetail | null;
  city_railway: TransitDetail | null;
  peak_travel_time_min: number | null;
  offpeak_travel_time_min: number | null;
}

export interface BuilderDetail {
  name: string;
  score: number;
  rera_projects: number;
  complaints: number;
  complaints_ratio: number;
  delivery_rating: string;
  active_in_area: boolean;
  avoid_reason?: string;
}

export interface BuilderScoreResult extends ScoreResult {
  builders: BuilderDetail[];
  recommended_builders: BuilderDetail[];
  builders_to_avoid: BuilderDetail[];
}

export interface AIVerification {
  confidence: number;
  narrative: string;
  verdict: string;
  pros: string[];
  cons: string[];
  best_for: string;
  avoid_if: string;
  flags: string[];
  verified_at?: string;
  model_used?: string;
}

export interface NeighborhoodRank {
  name: string;
  score: number;
  label: string;
  highlights: string[];
}

export interface RentVsBuyArea {
  area: string;
  recommendation: string;
  avg_2bhk_rent: number;
  monthly_emi: number;
  emi_rent_ratio: number;
  rental_yield_pct: number;
  avg_price_sqft: number;
}

export interface NeighborhoodScoreResponse {
  latitude: number;
  longitude: number;
  address: string;
  composite_score: number;
  composite_label: string;
  walkability: ScoreResult;
  safety: ScoreResult;
  hospital_access: ScoreResult;
  school_access: ScoreResult;
  transit_access: TransitScoreResult;
  builder_reputation: BuilderScoreResult;
  air_quality: ScoreResult;
  water_supply: ScoreResult;
  power_reliability: ScoreResult;
  future_infrastructure: ScoreResult;
  property_prices: ScoreResult;
  flood_risk: ScoreResult;
  commute: ScoreResult;
  delivery_coverage: ScoreResult;
  noise: ScoreResult;
  business_opportunity: ScoreResult;
  cleanliness: ScoreResult;
  ai_verification?: AIVerification;
  recommended_neighborhoods?: NeighborhoodRank[];
  neighborhoods_to_avoid?: NeighborhoodRank[];
  best_to_buy?: RentVsBuyArea[];
  best_to_rent?: RentVsBuyArea[];
  wards_covered?: WardInfo[];
  wards_total_population?: number;
}

export interface WardInfo {
  name: string;
  corporation: string;
  population?: number;
  distance_km?: number;
}
