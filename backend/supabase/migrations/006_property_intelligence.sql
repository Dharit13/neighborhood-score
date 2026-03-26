-- 006_property_intelligence.sql
-- Property Intelligence Platform: landmark_registry, commute_cache, enhanced builders, builder_projects, areas, infrastructure_projects

-- ============================================================
-- LANDMARK REGISTRY — unified destination lookup with aliases
-- ============================================================
CREATE TABLE IF NOT EXISTS landmark_registry (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    aliases         TEXT[] DEFAULT '{}',
    category        TEXT NOT NULL CHECK (category IN (
        'metro_station', 'tech_park', 'junction', 'area', 'airport',
        'hospital', 'school', 'mall', 'railway_station', 'bus_terminal'
    )),
    latitude        DECIMAL(10,7) NOT NULL,
    longitude       DECIMAL(10,7) NOT NULL,
    geog            GEOGRAPHY(Point, 4326),
    line            TEXT,
    status          TEXT DEFAULT 'operational',
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_landmarks_category ON landmark_registry(category);
CREATE INDEX IF NOT EXISTS idx_landmarks_name ON landmark_registry USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_landmarks_geog ON landmark_registry USING gist(geog);

-- Auto-populate geog from lat/lng
CREATE OR REPLACE FUNCTION landmark_set_geog()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geog := ST_Point(NEW.longitude, NEW.latitude)::geography;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_landmark_geog ON landmark_registry;
CREATE TRIGGER trg_landmark_geog
    BEFORE INSERT OR UPDATE ON landmark_registry
    FOR EACH ROW EXECUTE FUNCTION landmark_set_geog();

-- ============================================================
-- COMMUTE CACHE — point-to-point Maps API response caching
-- ============================================================
CREATE TABLE IF NOT EXISTS commute_cache (
    id                      SERIAL PRIMARY KEY,
    origin_lat              DECIMAL(10,4) NOT NULL,
    origin_lng              DECIMAL(10,4) NOT NULL,
    destination_lat         DECIMAL(10,4) NOT NULL,
    destination_lng         DECIMAL(10,4) NOT NULL,
    destination_name        TEXT,
    travel_mode             TEXT NOT NULL DEFAULT 'driving',
    peak_duration_seconds   INT,
    offpeak_duration_seconds INT,
    distance_meters         INT,
    crow_fly_distance_meters INT,
    queried_at              TIMESTAMPTZ DEFAULT now(),
    expires_at              TIMESTAMPTZ DEFAULT (now() + interval '7 days'),
    UNIQUE(origin_lat, origin_lng, destination_lat, destination_lng, travel_mode)
);

-- ============================================================
-- ENHANCED BUILDERS — richer schema for property intelligence
-- ============================================================
ALTER TABLE builders ADD COLUMN IF NOT EXISTS slug TEXT UNIQUE;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS also_known_as TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS cin VARCHAR(50);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS company_status VARCHAR(50);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS incorporated_date DATE;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS authorized_capital BIGINT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS paid_up_capital BIGINT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS rera_projects_completed INT DEFAULT 0;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS rera_projects_ongoing INT DEFAULT 0;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS rera_projects_delayed INT DEFAULT 0;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS revenue_range VARCHAR(50);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS profit_loss_trend VARCHAR(20);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS charges_registered INT DEFAULT 0;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS has_nclt_proceedings BOOLEAN DEFAULT FALSE;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS nclt_case_details TEXT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS consumer_court_cases INT DEFAULT 0;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS director_names TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS director_dins TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS directors_linked_to_failed BOOLEAN DEFAULT FALSE;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS director_risk_details TEXT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS review_sentiment_score DECIMAL(3,2);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS common_complaints TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS common_praise TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS trust_score INT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS trust_tier VARCHAR(20);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS trust_score_breakdown JSONB;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS segment VARCHAR(50);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS founded_year INT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS headquarters VARCHAR(100);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS website VARCHAR(255);
ALTER TABLE builders ADD COLUMN IF NOT EXISTS notable_projects TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS certifications TEXT[] DEFAULT '{}';
ALTER TABLE builders ADD COLUMN IF NOT EXISTS data_source TEXT;
ALTER TABLE builders ADD COLUMN IF NOT EXISTS data_last_refreshed TIMESTAMPTZ DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_builders_slug ON builders(slug);
CREATE INDEX IF NOT EXISTS idx_builders_trust_tier ON builders(trust_tier);
CREATE INDEX IF NOT EXISTS idx_builders_areas ON builders USING GIN(active_areas);

-- ============================================================
-- BUILDER PROJECTS — individual project tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS builder_projects (
    id                      SERIAL PRIMARY KEY,
    builder_id              INT REFERENCES builders(id) ON DELETE CASCADE,
    project_name            TEXT NOT NULL,
    slug                    TEXT,
    rera_number             VARCHAR(100),
    promoter_name           TEXT,
    location_area           VARCHAR(100),
    location_subarea        VARCHAR(100),
    full_address            TEXT,
    latitude                DECIMAL(10,7),
    longitude               DECIMAL(10,7),
    geog                    GEOGRAPHY(Point, 4326),
    district                VARCHAR(100),
    taluk                   VARCHAR(100),
    launch_date             DATE,
    rera_completion_date    DATE,
    actual_completion_date  DATE,
    delay_months            INT,
    status                  VARCHAR(50) DEFAULT 'ongoing',
    project_type            VARCHAR(100),
    price_per_sqft_min      INT,
    price_per_sqft_max      INT,
    unit_types              TEXT[] DEFAULT '{}',
    total_units             INT,
    avg_review_score        DECIMAL(2,1),
    review_count            INT DEFAULT 0,
    data_source             TEXT DEFAULT 'rera_scraper',
    data_last_refreshed     TIMESTAMPTZ DEFAULT now(),
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bp_builder ON builder_projects(builder_id);
CREATE INDEX IF NOT EXISTS idx_bp_area ON builder_projects(location_area);
CREATE INDEX IF NOT EXISTS idx_bp_status ON builder_projects(status);
CREATE INDEX IF NOT EXISTS idx_bp_rera ON builder_projects(rera_number);

-- ============================================================
-- AREAS — consolidated locality profiles
-- ============================================================
CREATE TABLE IF NOT EXISTS areas (
    id                              SERIAL PRIMARY KEY,
    name                            VARCHAR(100) NOT NULL,
    slug                            VARCHAR(100) UNIQUE NOT NULL,
    parent_area                     VARCHAR(100),
    latitude                        DECIMAL(10,7),
    longitude                       DECIMAL(10,7),
    geog                            GEOGRAPHY(Point, 4326),
    avg_price_per_sqft              INT,
    price_yoy_change_pct            DECIMAL(4,1),
    nearest_metro_station           VARCHAR(100),
    metro_distance_km               DECIMAL(4,1),
    metro_station_status            VARCHAR(50),
    hospitals_within_5km            INT,
    schools_within_5km              INT,
    waterlogging_risk               VARCHAR(20),
    water_supply_quality            VARCHAR(20),
    power_reliability               VARCHAR(20),
    description                     TEXT,
    known_for                       TEXT[] DEFAULT '{}',
    key_employers                   TEXT[] DEFAULT '{}',
    data_last_refreshed             TIMESTAMPTZ DEFAULT now(),
    created_at                      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_areas_slug ON areas(slug);

-- ============================================================
-- INFRASTRUCTURE PROJECTS — enhanced with realistic ETAs
-- ============================================================
CREATE TABLE IF NOT EXISTS infrastructure_projects (
    id                              SERIAL PRIMARY KEY,
    name                            TEXT NOT NULL,
    type                            VARCHAR(50),
    source_agency                   VARCHAR(100),
    announced_date                  DATE,
    official_completion_date        DATE,
    realistic_completion_date_low   DATE,
    realistic_completion_date_high  DATE,
    prediction_confidence           VARCHAR(20),
    prediction_rationale            TEXT,
    completion_percentage           DECIMAL(4,1),
    current_status                  VARCHAR(50),
    current_phase                   VARCHAR(50),
    last_progress_update            DATE,
    affected_areas                  TEXT[] DEFAULT '{}',
    route_description               TEXT,
    length_km                       REAL,
    cost_crore                      REAL,
    delay_multiplier                REAL,
    data_last_refreshed             TIMESTAMPTZ DEFAULT now(),
    created_at                      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_infra_areas ON infrastructure_projects USING GIN(affected_areas);
CREATE INDEX IF NOT EXISTS idx_infra_type ON infrastructure_projects(type);
