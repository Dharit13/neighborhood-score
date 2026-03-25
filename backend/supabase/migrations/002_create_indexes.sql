-- 002_create_indexes.sql
-- Spatial GIST indexes on all geography columns + B-tree on FK/query columns

-- Point tables — spatial indexes
CREATE INDEX IF NOT EXISTS idx_metro_stations_geog ON metro_stations USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_bus_stops_geog ON bus_stops USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_train_stations_geog ON train_stations USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_hospitals_geog ON hospitals USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_schools_geog ON schools USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_police_stations_geog ON police_stations USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_aqi_stations_geog ON aqi_stations USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_tech_parks_geog ON tech_parks USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_future_infra_stations_geog ON future_infra_stations USING GIST (geog);

-- Neighborhoods
CREATE INDEX IF NOT EXISTS idx_neighborhoods_geog ON neighborhoods USING GIST (center_geog);
CREATE INDEX IF NOT EXISTS idx_neighborhoods_name ON neighborhoods (name);

-- Zone tables — FK indexes + spatial
CREATE INDEX IF NOT EXISTS idx_safety_zones_neighborhood ON safety_zones (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_safety_zones_geog ON safety_zones USING GIST (center_geog);

CREATE INDEX IF NOT EXISTS idx_water_zones_neighborhood ON water_zones (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_water_zones_geog ON water_zones USING GIST (center_geog);

CREATE INDEX IF NOT EXISTS idx_power_zones_neighborhood ON power_zones (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_power_zones_geog ON power_zones USING GIST (center_geog);

CREATE INDEX IF NOT EXISTS idx_walkability_zones_neighborhood ON walkability_zones (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_walkability_zones_geog ON walkability_zones USING GIST (center_geog);

CREATE INDEX IF NOT EXISTS idx_property_prices_neighborhood ON property_prices (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_property_prices_geog ON property_prices USING GIST (center_geog);

CREATE INDEX IF NOT EXISTS idx_business_opportunity_neighborhood ON business_opportunity (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_business_opportunity_geog ON business_opportunity USING GIST (center_geog);

-- New buyer-perspective tables — FK indexes
CREATE INDEX IF NOT EXISTS idx_flood_risk_neighborhood ON flood_risk (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_commute_times_neighborhood ON commute_times (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_commute_times_tech_park ON commute_times (tech_park_id);
CREATE INDEX IF NOT EXISTS idx_delivery_coverage_neighborhood ON delivery_coverage (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_noise_zones_neighborhood ON noise_zones (neighborhood_id);

-- Infrastructure
CREATE INDEX IF NOT EXISTS idx_future_infra_stations_project ON future_infra_stations (project_id);

-- AQI readings — time-series query optimization
CREATE INDEX IF NOT EXISTS idx_aqi_readings_station ON aqi_readings (station_id);
CREATE INDEX IF NOT EXISTS idx_aqi_readings_time ON aqi_readings (recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_aqi_readings_station_time ON aqi_readings (station_id, recorded_at DESC);

-- Data freshness
CREATE INDEX IF NOT EXISTS idx_data_freshness_table ON data_freshness (table_name);

-- Builders
CREATE INDEX IF NOT EXISTS idx_builders_name ON builders (name);
CREATE INDEX IF NOT EXISTS idx_builders_score ON builders (score DESC);

-- Neighborhood verification
CREATE INDEX IF NOT EXISTS idx_neighborhood_verification_neighborhood ON neighborhood_verification (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_neighborhood_verification_time ON neighborhood_verification (verified_at DESC);
