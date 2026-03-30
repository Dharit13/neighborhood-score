# Backend — Neighbourhood Score API

FastAPI application powering 17-dimension neighborhood scoring for Bangalore.

## Directory Structure

```
backend/
  app/
    main.py              # FastAPI app, CORS, rate limiting
    config.py            # Score weights, Bangalore bbox, API keys
    db.py                # asyncpg connection pool
    models.py            # Pydantic request/response models
    cache.py             # Redis + in-memory cache layer
    routers/
      scores.py          # /api/scores, /api/prefetch, /api/verify-claims, /api/ai-recommend
      ai_chat.py         # /api/ai-chat (Claude streaming)
      property_intelligence.py  # /api/builders, /api/builder/:slug, /api/search
      report.py          # /api/generate-report
    scorers/             # 17 individual scoring modules
      air_quality.py
      builder.py
      business_opportunity.py
      cleanliness.py
      commute.py
      delivery_coverage.py
      flood_risk.py
      future_infra.py
      hospital.py
      noise.py
      power.py
      property_price.py
      safety.py
      school.py
      transit.py
      walkability.py
      water_supply.py
    pipelines/           # Data seeding, precomputation, scraping
      seed_all.py                # Master seeder — loads curated JSON into DB
      precompute_scores.py       # Runs all 17 scorers per neighborhood
      compute_trust_scores.py    # 5-dimension builder trust scores
      seed_neighborhoods.py      # Seed neighborhood boundaries
      seed_zones.py              # Seed zone data (safety, water, power, etc.)
      seed_prices.py             # Seed property price data
      seed_transit.py            # Seed transit/bus data
      seed_landmarks.py          # Seed landmark POIs
      seed_infra.py              # Seed infrastructure data
      seed_areas.py              # Seed area intelligence
      seed_curated_pois.py       # Seed curated points of interest
      seed_points.py             # Seed point data
      seed_infrastructure.py     # Seed infrastructure records
      geocode_neighborhoods.py   # Geocode neighborhood centroids
      fetch_aqi_hourly.py        # Fetch air quality index data
      fetch_bus_stops.py         # Fetch bus stop locations
      fetch_commute_times.py     # Fetch commute time estimates
      fetch_crime_data.py        # Fetch crime statistics
      fetch_delivery_coverage.py # Fetch delivery service coverage
      fetch_flood_risk.py        # Fetch flood risk zones
      fetch_google_places.py     # Fetch POIs from Google Places
      fetch_noise_zones.py       # Fetch noise level data
      fetch_parks.py             # Fetch park locations
      fetch_police_stations.py   # Fetch police station locations
      fetch_rera_builders.py     # Fetch RERA-registered builders
      fetch_reviews.py           # Fetch neighborhood reviews
      fetch_slum_data.py         # Fetch slum area data
      fetch_ward_mapping.py      # Fetch BBMP ward mappings
      fetch_waste_infra.py       # Fetch waste infrastructure
      fetch_compdata.py          # Fetch comparable property data
      pipeline_walkability.py    # Walkability score pipeline
      scrape_krera.py            # Scrape Karnataka RERA
      scrape_sitesetu.py         # Scrape SiteSetu listings
      enrich_builders_offline.py # Offline builder data enrichment
      runner.py                  # Pipeline orchestration
      verify_ai.py               # AI verification utilities
    utils/               # Geo utilities, Overpass API, helpers
    data/                # Curated JSON data files
      curated/           # Precomputed scores, neighborhood data
      raw/               # Raw source data
  tests/                 # pytest test suite
  supabase/migrations/   # SQL migration files (run in order)
```

## Quick Start

```bash
cp .env.example .env     # Configure API keys (see comments in file)
cd .. && make install-dev # Install Python + Node dependencies
make dev-backend          # Start uvicorn on :8000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/scores` | Full 17-dimension score for a location |
| GET | `/api/prefetch` | All neighborhood pins for map |
| GET | `/api/neighborhoods` | Neighborhood name list |
| POST | `/api/verify-claims` | Truth-check property ad claims |
| POST | `/api/ai-chat` | Claude streaming chat (SSE) |
| POST | `/api/generate-report` | PDF report data |
| POST | `/api/ai-recommend` | AI neighborhood recommendations |
| GET | `/api/builders` | List builders (filterable, paginated) |
| GET | `/api/builder/:slug` | Full builder profile |
| GET | `/api/area/:slug` | Area intelligence |
| POST | `/api/intelligence-brief` | AI buyer advisory |
| GET | `/api/search` | Global search |
| GET | `/api/config/map` | Google Maps config for frontend |
| GET | `/api/health` | Health check |

## Database

PostgreSQL + PostGIS on Supabase. Run migrations in order:

```bash
# In Supabase SQL Editor or psql:
001_create_tables.sql
002_create_indexes.sql
003_add_cleanliness.sql
004_add_ward_mapping.sql
005_google_places.sql
006_property_intelligence.sql
```

Key tables: `neighborhoods`, `safety_zones`, `walkability_zones`, `water_zones`, `power_zones`, `flood_risk`, `property_prices`, `noise_zones`, `builders`, `builder_projects`, `data_freshness`.

## Scoring Pipeline

1. `seed_all.py` — Seeds curated data from JSON files into database tables
2. `precompute_scores.py` — Runs all 17 scorers for each neighborhood, stores results
3. `compute_trust_scores.py` — Calculates 5-dimension builder trust scores

```bash
cd backend
uv run python -m app.pipelines.seed_all
uv run python -m app.pipelines.precompute_scores  # requires running backend
uv run python -m app.pipelines.compute_trust_scores
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `asyncpg.exceptions.ConnectionDoesNotExistError` | Check DB_HOST and DB_PASSWORD in .env |
| `Could not geocode address` | Verify GOOGLE_MAPS_API_KEY has Geocoding API enabled |
| Scorer returns None | Database table may be empty — run `seed_all` first |
| `ANTHROPIC_API_KEY not set` | Required for /ai-chat, /ai-recommend, /generate-report |
| `Rate limit exceeded (429)` | Built-in rate limiter — wait a few seconds |
