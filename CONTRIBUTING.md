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

## Adding a New Scoring Dimension

1. Create a scorer in `backend/app/scorers/`
2. Add the weight to `SCORE_WEIGHTS` in `backend/app/config.py`
3. Wire it into the scoring pipeline in `backend/app/routers/scores.py`
4. Add a frontend card in `frontend/src/components/`

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