-- 004_add_ward_mapping.sql
-- Map GBA 2025 wards (369) to neighborhoods for coverage display

CREATE TABLE IF NOT EXISTS ward_mapping (
    id              SERIAL PRIMARY KEY,
    neighborhood_id INTEGER REFERENCES neighborhoods(id) ON DELETE CASCADE,
    ward_name       TEXT NOT NULL,
    ward_name_kn    TEXT,
    corporation     TEXT NOT NULL,
    population      INTEGER,
    centroid_geog   GEOGRAPHY(Point, 4326),
    distance_km     REAL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ward_mapping_neighborhood ON ward_mapping (neighborhood_id);
CREATE INDEX IF NOT EXISTS idx_ward_mapping_centroid ON ward_mapping USING GIST (centroid_geog);
