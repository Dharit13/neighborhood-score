-- 003_add_cleanliness.sql
-- Neighborhood Cleanliness dimension: slum proximity + waste infrastructure

CREATE TABLE IF NOT EXISTS slum_zones (
    id              SERIAL PRIMARY KEY,
    fid             INTEGER,
    deprivation_dn  INTEGER CHECK (deprivation_dn >= 0 AND deprivation_dn <= 245),
    geog            GEOGRAPHY(Polygon, 4326) NOT NULL,
    centroid_geog   GEOGRAPHY(Point, 4326),
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS waste_infrastructure (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN (
        'dry_waste_centre','waste_processing','landfill','biomethanisation'
    )),
    geog            GEOGRAPHY(Point, 4326) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_slum_zones_centroid_geog ON slum_zones USING GIST (centroid_geog);
CREATE INDEX IF NOT EXISTS idx_slum_zones_geog ON slum_zones USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_waste_infra_geog ON waste_infrastructure USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_waste_infra_type ON waste_infrastructure (type);
