export interface FreshnessInfo {
  source: string | null;
  last_seeded: string | null;
  last_refreshed: string | null;
  record_count: number | null;
  status: string | null;
}

export type FreshnessData = Record<string, FreshnessInfo>;

const DIMENSION_TO_TABLES: Record<string, string[]> = {
  walkability: ['walkability_zones'],
  safety: ['safety_zones', 'police_stations'],
  hospital_access: ['hospitals'],
  school_access: ['schools'],
  transit_access: ['metro_stations', 'bus_stops', 'train_stations'],
  builder_reputation: ['builders'],
  air_quality: ['aqi_stations', 'aqi_readings'],
  water_supply: ['water_zones'],
  power_reliability: ['power_zones'],
  future_infrastructure: ['future_infra_projects', 'future_infra_stations'],
  property_prices: ['property_prices'],
  flood_risk: ['flood_risk'],
  commute: ['commute_times'],
  delivery_coverage: ['delivery_coverage'],
  noise: ['noise_zones'],
  business_opportunity: ['business_opportunity'],
  cleanliness: ['slum_zones', 'waste_infrastructure'],
};

export function getFreshnessForDimension(dimension: string, freshness: FreshnessData): string | null {
  const tables = DIMENSION_TO_TABLES[dimension];
  if (!tables) return null;

  let mostRecent: Date | null = null;

  for (const table of tables) {
    const info = freshness[table];
    if (!info) continue;
    const dateStr = info.last_refreshed || info.last_seeded;
    if (!dateStr) continue;
    const d = new Date(dateStr);
    if (!mostRecent || d > mostRecent) {
      mostRecent = d;
    }
  }

  if (!mostRecent) return null;

  const now = new Date();
  const diffMs = now.getTime() - mostRecent.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Updated today';
  if (diffDays === 1) return 'Updated yesterday';
  if (diffDays < 7) return `Updated ${diffDays}d ago`;
  if (diffDays < 30) return `Updated ${Math.floor(diffDays / 7)}w ago`;
  return `Updated ${mostRecent.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}`;
}
