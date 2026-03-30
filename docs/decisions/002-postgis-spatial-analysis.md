# ADR-002: PostGIS for Spatial Analysis

**Status:** Accepted
**Date:** 2025-11-20

## Context

Every scoring dimension requires answering spatial questions: "How far is this point from the nearest metro station?", "Which flood zone does this neighborhood fall in?", "What are the 3 closest AQI monitoring stations for IDW interpolation?"

Two approaches were considered:

1. **Simple distance calculations** — Haversine formula in Python, pre-compute distances in application code
2. **PostGIS spatial database** — Use PostgreSQL's geospatial extension with GIST indexes for native spatial queries

## Decision

We chose PostGIS (via Supabase's PostgreSQL) for all spatial computations.

### Why Not Simple Distance?

Haversine works for point-to-point distance but breaks down for our use cases:

- **KNN queries** ("nearest 3 hospitals within 5km") require scanning all points in Python — O(n) per query. PostGIS GIST indexes make this O(log n) with `ORDER BY geog <-> point LIMIT k`.
- **Radius searches** (`ST_DWithin`) are index-accelerated. Python equivalent requires loading all points into memory.
- **Geography type** handles Earth's curvature natively. Haversine is an approximation that accumulates error at Bangalore's latitude (12.97°N).
- **Consistent units** — `ST_Distance` returns meters directly. No unit conversion bugs.

### Implementation

All geospatial columns use `GEOGRAPHY(Point, 4326)` (WGS84 datum). GIST indexes on every spatial column:

```sql
CREATE INDEX idx_metro_stations_geog ON metro_stations USING GIST (geog);
CREATE INDEX idx_neighborhoods_geog ON neighborhoods USING GIST (center_geog);
-- 40+ spatial indexes total
```

Spatial query patterns used:

| Pattern | SQL | Use Case |
|---------|-----|----------|
| Nearest-K | `ORDER BY geog <-> ST_Point($1,$2)::geography LIMIT $3` | Nearest metro, hospital, school |
| Radius search | `ST_DWithin(geog, point, $3)` | All POIs within 2km |
| Distance | `ST_Distance(geog, point)` | Exact distance in meters |
| IDW interpolation | Distance from 3 nearest stations → `1/max(d, 0.1)` weights | Air quality scoring |

### Pre-computed Zones

Zone scores (safety, water, walkability, power, flood, noise) are pre-seeded into `*_zones` tables during data pipelines. Scorer functions read these zones at request time — no expensive spatial computation on the hot path.

## Consequences

- Sub-millisecond spatial queries even with 130+ neighborhoods × 1000+ POIs
- Correct Earth-curvature distance calculations without approximation
- Database handles spatial indexing — application code stays simple
- Requires Supabase (or any PostgreSQL with PostGIS) — not portable to SQLite
- 6 SQL migrations manage schema evolution including spatial indexes
