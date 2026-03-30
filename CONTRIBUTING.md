# Contributing

Thanks for your interest in contributing! Here's how to get started.

## Setup

1. Fork and clone the repo
2. Install [uv](https://docs.astral.sh/uv/) and copy environment files:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   # Edit both .env files with your own API keys
   ```
3. Install dependencies:
   ```bash
   make install-dev
   ```

## Database Setup

You need a Supabase project (or any PostgreSQL with PostGIS). Run the migrations in order:

```bash
# In Supabase SQL Editor (or psql), run each file in order:
backend/supabase/migrations/001_create_tables.sql
backend/supabase/migrations/002_create_indexes.sql
backend/supabase/migrations/003_add_cleanliness.sql
backend/supabase/migrations/004_add_ward_mapping.sql
backend/supabase/migrations/005_google_places.sql
backend/supabase/migrations/006_property_intelligence.sql
```

Then seed the data:

```bash
cd backend
uv run python -m app.pipelines.seed_all
```

To precompute neighborhood scores (required for the map and AI recommender):

```bash
# Start the backend first
make dev-backend

# In another terminal
cd backend && uv run python -m app.pipelines.precompute_scores
```

## Running

```bash
make dev-backend    # terminal 1 — uvicorn on :8000
make dev-frontend   # terminal 2 — vite on :5173 (proxies /api to :8000)
```

## Pull Request Rules

- **Branch from `main`**, target `main`
- Keep PRs focused on a single change
- Run `make check` before submitting (lint + typecheck + tests)
- Fill out the PR template — explain what, why, and how
- At least **1 maintainer approval** required before merge
- CI must pass (backend + frontend jobs)
- **Squash merge** preferred — keeps history clean
- No direct pushes to `main`
- Commit messages: imperative mood, concise subject line (<72 chars)
  - Good: `Add flood risk scorer with BBMP ward data`
  - Bad: `updated stuff`

## Ways to Contribute

### 1. Add or Improve Neighborhood Data

We currently score **130+ neighborhoods across 17 dimensions**. The biggest impact comes from better data.

#### Curated Data Files (`backend/app/data/curated/`)

These JSON files are the easiest entry point — no API keys needed, just local knowledge:

| File | What it contains | How to improve |
|------|-----------------|----------------|
| `safety_zones.json` | Crime rates, police station coverage | Add missing police stations, update crime stats from NCRB/KSP reports |
| `water_zones.json` | BWSSB stage classifications, supply hours | Update supply schedules, add borewell/tanker dependency data |
| `power_zones.json` | BESCOM tier ratings, outage frequency | Add recent outage data, transformer capacity |
| `property_prices.json` | Avg ₹/sqft, 2BHK prices, rent, YoY growth | Update with latest RERA/ANAROCK/MagicBricks data |
| `walkability_zones.json` | Footpath quality, street lighting, crossing density | Ground-truth walkability from walking audits |
| `top_schools.json` | CBSE/ICSE/State board schools with ratings | Add missing schools, update ratings, add fee ranges |
| `nabh_hospitals.json` | NABH-accredited hospitals, bed counts | Add clinics, specialty hospitals, ambulance response times |
| `metro_stations.json` | Namma Metro stations with coordinates | Add Phase 2/3 stations as they open |
| `bus_stops.json` | BMTC bus stop locations | Add missing stops, route frequency data |
| `aqi_stations.json` | CPCB air quality monitoring stations | Add more station data, seasonal AQI patterns |
| `police_stations.json` | Station locations and jurisdiction | Add beat-level patrol data |
| `future_infra.json` | Upcoming infrastructure projects | Add timeline updates, new announced projects (PRR, metro extensions) |
| `builders.json` | Builder profiles, RERA compliance | Add builder reviews, project delivery track records |
| `business_opportunity.json` | Coworking spaces, startup density | Add new coworking/tech parks, startup ecosystem data |
| `landmarks.json` | Key landmarks for geocoding reference | Add missing landmarks, popular local references |
| `areas.json` | Area boundaries and metadata | Add sub-locality boundaries, pin code mappings |

#### How to submit data improvements

1. Fork the repo, edit the JSON file in `backend/app/data/curated/`
2. Keep the existing JSON schema — add entries, don't change the structure
3. Include your data source in the PR description (e.g., "BWSSB 2025 report", "ground survey Dec 2025")
4. Run `make check` to ensure nothing breaks
5. Submit a PR targeting `main`

### 2. Add a New Scoring Dimension

We currently have 17 dimensions. Ideas for new ones:

| Dimension | Data Source Ideas | Impact |
|-----------|------------------|--------|
| **Pet-friendliness** | Parks with pet areas, vet clinics, pet stores | Growing demand from young buyers |
| **Internet quality** | ISP coverage (ACT, Airtel Fiber), avg speeds | Remote work is a top priority |
| **Nightlife/dining** | Restaurant density, bar/pub clusters, Zomato/Swiggy delivery times | Lifestyle scoring |
| **Senior-friendliness** | Accessibility, pharmacy density, geriatric care, park benches | Retirement/elderly housing |
| **Green cover** | Tree canopy %, parks per capita, lake proximity | Environmental quality |
| **Traffic congestion** | Google Maps typical travel times, peak hour data | Commute quality beyond transit access |
| **Rental ROI** | Rental yield %, vacancy rates, tenant demand | Investor-focused scoring |

**Steps to add a new dimension:**

1. Create a scorer in `backend/app/scorers/your_dimension.py`
2. Add curated data in `backend/app/data/curated/your_data.json`
3. Add a seed pipeline in `backend/app/pipelines/seed_your_data.py`
4. Add the weight to `SCORE_WEIGHTS` in `backend/app/config.py`
5. Wire it into the scoring pipeline in `backend/app/routers/scores.py`
6. Add a frontend card in `frontend/src/components/`
7. Add a migration if new DB tables are needed in `backend/supabase/migrations/`

### 3. Enhance Existing Scorers

Each scorer in `backend/app/scorers/` computes a 0–100 score. Improvements could include:

- **Better algorithms**: The safety scorer uses crime rate + police proximity — could add CCTV density, street lighting
- **More data sources**: The air quality scorer uses CPCB stations — could integrate SAFAR or purple air sensors
- **Temporal awareness**: Scores are static — add time-of-day or seasonal variation (e.g., flood risk during monsoon)
- **Hyperlocal granularity**: Most scorers work at neighborhood level — could go down to ward or pin code level

### 4. Frontend & UX

- Improve mobile responsiveness
- Add comparison views (side-by-side neighborhoods)
- Better data visualization (charts, heatmaps)
- Accessibility improvements (WCAG compliance)
- Localization (Kannada, Hindi)

### 5. Data Pipelines

Pipelines in `backend/app/pipelines/` fetch and process data. You can:

- Add new fetch pipelines for open data sources (data.opencity.in, data.gov.in, BBMP open data)
- Improve geocoding accuracy in `geocode_neighborhoods.py`
- Add data validation and freshness checks
- Optimize pipeline performance (batch processing, caching)

### 6. Infrastructure & DevOps

- Add monitoring/alerting
- Improve CI/CD pipeline
- Add load testing
- Database query optimization
- API documentation improvements

## Reporting Bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Browser/OS if frontend-related

## Code Style

- **Python**: Follow ruff defaults
- **TypeScript**: Follow the existing ESLint config

## Branch Protection (Maintainers)

If you're setting up the repo on GitHub, enable these on `main`:

- Require pull request reviews (1 approval)
- Require status checks to pass: `backend`, `frontend`
- Require branches to be up-to-date before merging
- Block force pushes
- Block branch deletion

## Running Pipelines Locally

Individual data pipelines can be run from the `backend/` directory:

```bash
cd backend

# Seed all curated data into the database
uv run python -m app.pipelines.seed_all

# Precompute neighborhood scores (requires backend running on :8000)
uv run python -m app.pipelines.precompute_scores

# Compute builder trust scores
uv run python -m app.pipelines.compute_trust_scores

# Seed curated POIs (points of interest)
uv run python -m app.pipelines.seed_curated_pois
```

Pipelines are idempotent — safe to re-run. They use `INSERT ... ON CONFLICT` to upsert.

## Local Supabase (Optional)

You can use the [Supabase CLI](https://supabase.com/docs/guides/cli) for fully local development:

```bash
# Install Supabase CLI
brew install supabase/tap/supabase

# Start local Supabase (PostgreSQL + PostGIS + Auth + Storage)
supabase start

# Use the local connection string in backend/.env:
# DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres
# DB_HOST=127.0.0.1
# DB_PORT=54322
# DB_USER=postgres
# DB_PASSWORD=postgres

# Run migrations
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres -f supabase/migrations/001_create_tables.sql
# ... repeat for each migration file in order

# Stop when done
supabase stop
```

## Debugging Guide

### Backend

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ConnectionRefusedError` on startup | Database not reachable | Check `DB_HOST`, `DB_PORT`, `DB_PASSWORD` in `.env` |
| `Could not geocode address` | Google Maps API issue | Verify `GOOGLE_MAPS_API_KEY` has Geocoding API enabled in Cloud Console |
| Scorer returns `None` or score is 0 | Empty database table | Run `uv run python -m app.pipelines.seed_all` |
| `ANTHROPIC_API_KEY not set` warning | Missing env var | Add key to `.env` — required for `/ai-chat`, `/ai-recommend`, `/generate-report` |
| `429 Too Many Requests` | Rate limiter triggered | Built-in protection — wait 2-5 seconds and retry |

### Frontend

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Map shows gray/blank | Missing or invalid Google Maps key | Backend must be running — frontend gets the key from `/api/config/map` |
| CORS errors in console | Backend not running or wrong port | Start backend on `:8000` — Vite proxies `/api` there |
| Login redirects fail | Supabase URL/key mismatch | Check `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env` |
| Scores show as 0 | Precomputed scores not generated | Run `precompute_scores` pipeline with backend running |
| Build fails with type errors | TypeScript strict mode | Run `npx tsc -b --noEmit` to see all errors, fix before committing |

## Testing Individual Scorers

Each scorer can be tested in isolation:

```python
# In a Python shell (from backend/ directory)
from dotenv import load_dotenv; load_dotenv()

import asyncio
from app.db import get_pool
from app.scorers.safety import compute as safety_score

async def test():
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await safety_score(12.9716, 77.5946, conn)  # Bangalore center
        print(result)

asyncio.run(test())
```