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

export interface LifestyleTag {
  category: string;
  label: string;
  detail: string;
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
  lifestyle_tags?: LifestyleTag[];
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

export interface FeaturedNeighborhood {
  name: string;
  latitude: number;
  longitude: number;
  score: number;
  label: string;
  avg_price_sqft: number | null;
  yoy_growth_pct: number | null;
  safety_score?: number;
}

// ─── Property Intelligence Types ─────────────────────────────

export interface ClaimVerification {
  original_claim: string;
  claimed_value: string;
  actual_value: string;
  difference: string;
  verdict: 'ACCURATE' | 'SLIGHTLY_OPTIMISTIC' | 'MISLEADING' | 'SIGNIFICANTLY_MISLEADING' | 'UNRESOLVED' | string;
  details: {
    destination?: string;
    destination_category?: string;
    resolution_method?: string;
    peak_duration_min?: number;
    offpeak_duration_min?: number;
    road_distance_km?: number;
    straight_line_km?: number;
    ratio?: number;
    reality_gap_multiplier?: number;
    explanation?: string;
    data_source?: string;
    destination_lat?: number;
    destination_lng?: number;
    nearest?: string;
    note?: string;
  };
}

export interface VerifyClaimsResponse {
  latitude: number;
  longitude: number;
  address: string;
  results: ClaimVerification[];
  summary: string;
  narrative: string;
  extracted_claims: string[];
}

export interface BuilderSummary {
  name: string;
  slug: string | null;
  trust_score: number | null;
  trust_tier: string | null;
  segment: string | null;
  rera_projects: number;
  complaints: number;
  complaints_ratio: number;
  on_time_delivery_pct: number;
  avg_rating: number | null;
  active_areas: string[];
  notable_projects: string[];
  trust_score_breakdown: Record<string, number> | null;
}

export interface BuilderProject {
  project_name: string;
  rera_number: string | null;
  location_area: string | null;
  status: string;
  delay_months: number | null;
}

export interface RiskFlag {
  severity: 'critical' | 'warning' | 'info';
  title: string;
  detail: string;
}

export interface BuilderProfile extends BuilderSummary {
  has_nclt_proceedings: boolean;
  nclt_case_details?: string;
  consumer_court_cases: number;
  directors_linked_to_failed: boolean;
  director_risk_details?: string;
  review_sentiment_score: number | null;
  common_complaints: string[];
  common_praise: string[];
  description: string | null;
  founded_year: number | null;
  website: string | null;
  certifications: string[];
  projects: BuilderProject[];
  risk_flags: RiskFlag[];
}

export interface BuildersResponse {
  total: number;
  builders: Record<string, BuilderSummary[]>;
  filters: { area?: string; tier?: string; segment?: string };
  area_summary?: string;
  builder_briefs?: Record<string, string>;
}

export interface InfraProject {
  name: string;
  type: string;
  official_completion_date?: string;
  realistic_completion_date_low?: string;
  realistic_completion_date_high?: string;
  completion_percentage: number;
  current_status: string;
  prediction_confidence?: string;
  affected_areas: string[];
  route_description?: string;
  delay_multiplier?: number;
}

export interface AreaResponse {
  area: Record<string, unknown>;
  builders: BuilderSummary[];
  infrastructure: InfraProject[];
  property_prices: Record<string, unknown> | null;
}

export interface IntelligenceBrief {
  verdict: string;
  brief: string;
  key_strengths: string[];
  key_risks: string[];
  price_assessment: string;
  address?: string;
}

export interface SearchResults {
  query: string;
  total: number;
  results: {
    builders: { name: string; slug: string; trust_score: number; trust_tier: string; segment: string }[];
    projects: { project_name: string; slug: string; location_area: string; status: string; rera_number: string }[];
    areas: { name: string; latitude: number; longitude: number }[];
    landmarks: { name: string; category: string; latitude: number; longitude: number }[];
  };
}
