-- 001_create_tables.sql
-- Bangalore Neighborhood Score Calculator — full schema with PostGIS
-- Run against Supabase PostgreSQL (PostGIS is pre-installed)

CREATE EXTENSION IF NOT EXISTS postgis;

-- ============================================================
-- MASTER TABLE: neighborhoods
-- ============================================================
CREATE TABLE IF NOT EXISTS neighborhoods (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    aliases         TEXT[] DEFAULT '{}',
    center_geog     GEOGRAPHY(Point, 4326) NOT NULL,
    radius_km       REAL NOT NULL DEFAULT 2.0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- POINT TABLES (lat/lon with PostGIS geography column)
-- ============================================================

CREATE TABLE IF NOT EXISTS metro_stations (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    line            TEXT NOT NULL,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    status          TEXT DEFAULT 'operational' CHECK (status IN ('operational','construction','planned')),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bus_stops (
    id              SERIAL PRIMARY KEY,
    stop_id         TEXT,
    name            TEXT NOT NULL,
    ward            TEXT,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS train_stations (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT DEFAULT 'suburban' CHECK (type IN ('major','suburban')),
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hospitals (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    accreditation   TEXT,
    tier            INTEGER DEFAULT 1,
    specialties     TEXT[] DEFAULT '{}',
    beds            INTEGER,
    area            TEXT,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS schools (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    board           TEXT,
    rank            INTEGER,
    rank_score      INTEGER,
    area            TEXT,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    fee_range_lakh_pa TEXT,
    seats           INTEGER,
    admission_difficulty TEXT CHECK (admission_difficulty IN ('easy','moderate','competitive','very_competitive')),
    admission_window TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS police_stations (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT DEFAULT 'station',
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aqi_stations (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    area            TEXT,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    avg_aqi         REAL,
    primary_pollutant TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aqi_readings (
    id              SERIAL PRIMARY KEY,
    station_id      INTEGER NOT NULL REFERENCES aqi_stations(id) ON DELETE CASCADE,
    recorded_at     TIMESTAMPTZ NOT NULL,
    aqi             REAL,
    pm25            REAL,
    pm10            REAL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tech_parks (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    company_count   INTEGER,
    employee_estimate INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- ZONE TABLES (area-level scores linked to neighborhoods)
-- ============================================================

CREATE TABLE IF NOT EXISTS safety_zones (
    id                      SERIAL PRIMARY KEY,
    neighborhood_id         INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    zone_name               TEXT NOT NULL,
    crime_rate_per_100k     REAL,
    streetlight_pct         REAL,
    cctv_density_per_sqkm   REAL,
    police_density_per_sqkm REAL,
    score                   REAL,
    center_geog             GEOGRAPHY(Point, 4326),
    radius_km               REAL DEFAULT 3.0,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS water_zones (
    id                  SERIAL PRIMARY KEY,
    neighborhood_id     INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    area                TEXT NOT NULL,
    stage               INTEGER,
    supply_hours        REAL,
    reliability         TEXT CHECK (reliability IN ('high','medium','low','very_low')),
    score               REAL,
    center_geog         GEOGRAPHY(Point, 4326),
    radius_km           REAL DEFAULT 2.0,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS power_zones (
    id                          SERIAL PRIMARY KEY,
    neighborhood_id             INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    area                        TEXT NOT NULL,
    tier                        INTEGER,
    avg_monthly_outage_hours    REAL,
    score                       REAL,
    center_geog                 GEOGRAPHY(Point, 4326),
    radius_km                   REAL DEFAULT 2.0,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS walkability_zones (
    id                  SERIAL PRIMARY KEY,
    neighborhood_id     INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    area                TEXT NOT NULL,
    score               REAL,
    center_geog         GEOGRAPHY(Point, 4326),
    radius_km           REAL DEFAULT 2.0,
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS property_prices (
    id                      SERIAL PRIMARY KEY,
    neighborhood_id         INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    area                    TEXT NOT NULL,
    avg_price_sqft          INTEGER,
    price_range_low         INTEGER,
    price_range_high        INTEGER,
    avg_2bhk_lakh           INTEGER,
    avg_3bhk_lakh           INTEGER,
    avg_2bhk_rent           INTEGER,
    avg_3bhk_rent           INTEGER,
    avg_maintenance_monthly INTEGER,
    yoy_growth_pct          REAL,
    rental_yield_pct        REAL,
    emi_to_income_pct       REAL,
    affordability_score     REAL,
    affordability_label     TEXT,
    resale_avg_days_on_market INTEGER,
    center_geog             GEOGRAPHY(Point, 4326),
    radius_km               REAL DEFAULT 2.0,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS builders (
    id                      SERIAL PRIMARY KEY,
    name                    TEXT NOT NULL UNIQUE,
    rera_projects           INTEGER DEFAULT 0,
    total_projects_blr      INTEGER DEFAULT 0,
    complaints              INTEGER DEFAULT 0,
    complaints_ratio        REAL DEFAULT 0,
    on_time_delivery_pct    INTEGER DEFAULT 0,
    avg_rating              REAL,
    reputation_tier         TEXT,
    active_areas            TEXT[] DEFAULT '{}',
    score                   REAL,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS business_opportunity (
    id                              SERIAL PRIMARY KEY,
    neighborhood_id                 INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    area                            TEXT NOT NULL,
    new_business_acceptability_pct  REAL,
    commercial_rent_sqft            REAL,
    footfall_index                  REAL,
    startup_density                 REAL,
    coworking_spaces                INTEGER,
    consumer_spending_index         REAL,
    business_type_fit               TEXT[] DEFAULT '{}',
    score                           REAL,
    label                           TEXT,
    center_geog                     GEOGRAPHY(Point, 4326),
    radius_km                       REAL DEFAULT 2.0,
    created_at                      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- NEW BUYER-PERSPECTIVE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS flood_risk (
    id                      SERIAL PRIMARY KEY,
    neighborhood_id         INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    risk_level              TEXT CHECK (risk_level IN ('low','moderate','high','very_high')),
    flood_history_events    INTEGER DEFAULT 0,
    elevation_m             REAL,
    drainage_quality        TEXT CHECK (drainage_quality IN ('good','poor','critical')),
    waterlogging_prone_spots TEXT[] DEFAULT '{}',
    bbmp_flood_ward         BOOLEAN DEFAULT FALSE,
    score                   REAL,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS commute_times (
    id                  SERIAL PRIMARY KEY,
    neighborhood_id     INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    tech_park_id        INTEGER REFERENCES tech_parks(id) ON DELETE CASCADE,
    mode                TEXT NOT NULL CHECK (mode IN ('car_peak','car_offpeak','metro','bus_metro','bike')),
    duration_min        REAL,
    distance_km         REAL,
    route_summary       TEXT,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (neighborhood_id, tech_park_id, mode)
);

CREATE TABLE IF NOT EXISTS delivery_coverage (
    id                      SERIAL PRIMARY KEY,
    neighborhood_id         INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    swiggy_serviceable      BOOLEAN DEFAULT FALSE,
    zepto_serviceable       BOOLEAN DEFAULT FALSE,
    blinkit_serviceable     BOOLEAN DEFAULT FALSE,
    bigbasket_serviceable   BOOLEAN DEFAULT FALSE,
    avg_delivery_min        REAL,
    coverage_score          REAL,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS noise_zones (
    id                          SERIAL PRIMARY KEY,
    neighborhood_id             INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    airport_flight_path         BOOLEAN DEFAULT FALSE,
    highway_proximity_km        REAL,
    construction_zones_active   INTEGER DEFAULT 0,
    avg_noise_db_estimate       REAL,
    noise_label                 TEXT CHECK (noise_label IN ('quiet','moderate','noisy','very_noisy')),
    score                       REAL,
    created_at                  TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- INFRASTRUCTURE TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS future_infra_projects (
    id                      SERIAL PRIMARY KEY,
    name                    TEXT NOT NULL,
    type                    TEXT NOT NULL CHECK (type IN ('metro','suburban_rail','expressway')),
    status                  TEXT DEFAULT 'planning' CHECK (status IN ('operational','under_construction','planning')),
    expected_completion     TEXT,
    length_km               REAL,
    cost_crore              REAL,
    description             TEXT,
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS future_infra_stations (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES future_infra_projects(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- SYSTEM TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS neighborhood_verification (
    id                  SERIAL PRIMARY KEY,
    neighborhood_id     INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    confidence          INTEGER DEFAULT 0 CHECK (confidence >= 0 AND confidence <= 100),
    flags               JSONB DEFAULT '[]',
    narrative           TEXT,
    verified_at         TIMESTAMPTZ DEFAULT now(),
    model_used          TEXT DEFAULT 'claude-sonnet-4-20250514',
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (neighborhood_id)
);

CREATE TABLE IF NOT EXISTS data_freshness (
    id                  SERIAL PRIMARY KEY,
    source_name         TEXT NOT NULL,
    table_name          TEXT NOT NULL,
    last_seeded_at      TIMESTAMPTZ,
    last_refreshed_at   TIMESTAMPTZ,
    record_count        INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'fresh' CHECK (status IN ('fresh','stale','error')),
    next_refresh_at     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source_name, table_name)
);
