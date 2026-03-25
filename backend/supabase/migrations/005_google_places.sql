-- 005_google_places.sql
-- Unified POI table fed by Google Places bulk pipeline.
-- Replaces per-category point tables (schools, hospitals, police_stations, etc.)
-- with a single table using a tags JSONB column for quality metadata.

CREATE TABLE IF NOT EXISTS pois (
    id                  SERIAL PRIMARY KEY,
    place_id            TEXT UNIQUE,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,
    geog                GEOGRAPHY(Point, 4326) NOT NULL,
    rating              REAL,
    user_ratings_total  INTEGER DEFAULT 0,
    tags                JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pois_geog ON pois USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_pois_category ON pois (category);
CREATE INDEX IF NOT EXISTS idx_pois_place_id ON pois (place_id);
CREATE INDEX IF NOT EXISTS idx_pois_tags ON pois USING GIN (tags);
