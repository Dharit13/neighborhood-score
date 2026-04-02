# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Requirements: Python 3.12+, Node.js 20+, PostgreSQL with PostGIS

Neighborhood Score is a data-driven neighborhood scoring platform for Bangalore home buyers. Scores 126 neighborhoods across 17 livability dimensions using curated data, PostGIS spatial analysis, and Claude AI verification.

Core Concepts:

- **Scorers** compute 0-100 scores for each neighborhood across 17 dimensions (safety, walkability, transit, etc.)
- **Pipelines** seed curated data into PostgreSQL and precompute neighborhood scores
- **Routers** expose FastAPI endpoints for scoring, AI chat, claim verification, and builder intelligence
- Simple flow: curated JSON data → seed pipeline → PostGIS tables → scorer → composite score → API → frontend map

## Architecture

- **Backend**: Python 3.12, FastAPI, asyncpg (PostgreSQL + PostGIS via Supabase)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS 4
- **AI**: Anthropic Claude SDK (direct — no LiteLLM or wrappers)
- **Database**: Supabase (PostgreSQL + PostGIS), see [DATABASE.md](DATABASE.md) for non-Supabase setup
- **Auth**: Supabase JWT (ES256 signing with public JWK verification)

## Development Commands

Use `uv` for all Python commands and `npm` for frontend.

### Setup and Installation

```bash
# Install all dependencies (backend + frontend)
make install-dev

# Configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit both .env files with your API keys
```

### Running

```bash
make dev-backend    # Start backend (uvicorn on :8000)
make dev-frontend   # Start frontend (vite on :5173, proxies /api to :8000)
```

### Testing

```bash
# Run all tests (backend + frontend)
make test

# Backend tests only
cd backend && uv run pytest tests/ -v

# Run specific test file
cd backend && uv run pytest tests/test_api.py -v

# Run tests matching pattern
cd backend && uv run pytest -k "test_pattern"

# Frontend tests
cd frontend && npx vitest run
```

### Linting and Formatting

```bash
# Lint backend + frontend
make lint

# Auto-format backend code
make format

# Type check backend + frontend
make typecheck

# Backend-specific
cd backend && uv run ruff check .           # Lint
cd backend && uv run ruff format .          # Format
cd backend && uv run ruff check --fix .     # Lint with auto-fix
cd backend && uv run ty check               # Type check

# Frontend-specific
cd frontend && npm run lint                 # ESLint
cd frontend && npx tsc -b --noEmit          # TypeScript check
```

### Security

```bash
# Run all security checks (dependency audit + SAST)
make security

# Individual checks
cd backend && uv audit                      # Python dependency audit
cd backend && uv run bandit -r app/ -c pyproject.toml  # Python SAST
cd frontend && npm audit --audit-level=high # Node dependency audit
```

### All Checks (CI equivalent)

```bash
# Run ALL checks — lint + typecheck + test + security
make check
```

## Code Style

### Python (backend/)

- **Formatter/Linter**: ruff (line-length 120, rules: E, F, I, UP)
- **Type checker**: ty (Python 3.12)
- **Async**: Use `async def` for all route handlers and DB calls
- **DB queries**: Always use parameterized queries (`$1`/`%s` placeholders) — never string interpolation
- **Imports**: `load_dotenv()` must run before importing app modules that read env vars
- **Scores**: All dimension scores must be 0-100 range. Weights defined in `config.py` sum to 1.0

### TypeScript (frontend/)

- **Linter**: ESLint with typescript-eslint
- **Styles**: Tailwind CSS 4 utility classes
- **State**: React hooks, no external state management
- **API calls**: Use fetch with `/api/` prefix (Vite proxies to backend)

## File Structure

```
backend/
  app/
    main.py              # FastAPI app, CORS, rate limiter
    config.py            # Score weights (17 dimensions), model config
    db.py                # asyncpg connection pool
    auth.py              # Supabase JWT (ES256) authentication
    cache.py             # Optional Redis caching layer
    routers/
      scores.py          # Core scoring endpoint (17-dimension composite)
      ai_chat.py         # Claude AI streaming chat
      report.py          # AI-generated PDF report data
      builders.py        # Builder profiles, trust scores, search
      claims.py          # Property ad claim verification
      health.py          # Health check endpoint
    scorers/             # 17 scoring dimension modules (each returns 0-100)
      safety.py          # Crime rate, police proximity, CCTV density
      transit.py         # Metro/bus/train proximity (MOHUA TOD norms)
      walkability.py     # NEWS-India framework, OSM data
      flood_risk.py      # BBMP flood spots, elevation data
      commute.py         # Google Distance Matrix to tech parks
      air_quality.py     # CPCB AQI stations (IDW interpolation)
      hospital.py        # NABH hospitals, bed density
      water.py           # BWSSB stage classification
      school.py          # RTE norms, ranked schools
      affordability.py   # EMI-to-income ratio
      noise.py           # Airport flight paths, highway proximity
      power.py           # BESCOM tier classification
      future_infra.py    # Metro/road project proximity
      cleanliness.py     # Slum density, waste infrastructure
      builder_reputation.py  # RERA compliance
      delivery.py        # Quick commerce coverage
      business.py        # Startup density, coworking
    pipelines/           # Data seeding and precomputation
      seed_all.py        # Master seeder (runs all seeders + migrations)
      runner.py          # Migration runner
      precompute_scores.py  # Precompute and cache all neighborhood scores
      compute_trust_scores.py  # Builder trust score computation
    data/curated/        # JSON data files (easiest contribution entry point)
    utils/               # Shared helpers (geo, overpass, etc.)
  tests/                 # pytest tests (async, mocked DB pool)
  supabase/migrations/   # 6 SQL migration files (run in order: 001-006)
frontend/
  src/
    components/          # React components (score cards, charts, map)
    pages/               # Route pages
    hooks/               # Custom React hooks
    utils/               # Frontend helpers
```

## Key Conventions

1. **No wrapper libraries for AI** — Use Anthropic SDK directly (supply chain security reason: LiteLLM was compromised in March 2026)
2. **Environment variables for all secrets** — Never hardcode keys, passwords, or URLs
3. **Parameterized SQL everywhere** — No f-strings or `.format()` in queries
4. **Run `make check` before submitting PRs** — Must pass lint, typecheck, tests, and security
5. **Commit messages**: Imperative mood, <72 chars (e.g., "Add flood risk scorer with BBMP ward data")
6. **PRs target `master`**, squash merge preferred
7. **Pipelines are idempotent** — Use `INSERT ... ON CONFLICT` to upsert
8. **Scores are 0-100** — All scorers return values in this range, weights sum to 1.0

## Security Rules

- Never commit `.env` files or credentials
- Never add LiteLLM or similar API key aggregation libraries
- All new dependencies must pass `uv audit` / `npm audit`
- Use `bandit` to check for Python security issues before merging
- API keys are server-side only — never expose to frontend except via `/api/config/map`
- JWT auth uses ES256 (Supabase ECC P-256 signing key), not HS256

## Testing

- Backend tests in `backend/tests/` using pytest with async support (`asyncio_mode = "auto"`)
- Run with `make test` or `cd backend && uv run pytest tests/ -v`
- Mock the database connection pool in tests, not external APIs
- Auth is mocked in tests via `app.dependency_overrides[require_auth]`

## Adding a New Scoring Dimension

1. Create a scorer in `backend/app/scorers/your_dimension.py` (must return 0-100)
2. Add curated data in `backend/app/data/curated/your_data.json`
3. Add a seed pipeline in `backend/app/pipelines/seed_your_data.py`
4. Add the weight to `SCORE_WEIGHTS` in `backend/app/config.py` (all weights must sum to 1.0)
5. Wire it into the scoring pipeline in `backend/app/routers/scores.py`
6. Add a frontend card in `frontend/src/components/`
7. Add a migration if new DB tables are needed in `backend/supabase/migrations/`

## Database

- 33 PostGIS-enabled tables across scoring, property intelligence, and infrastructure
- Migrations in `backend/supabase/migrations/` — run in numbered order (001-006)
- Seed data: `cd backend && uv run python -m app.pipelines.seed_all`
- Precompute scores: `cd backend && uv run python -m app.pipelines.precompute_scores`
- See [DATABASE.md](DATABASE.md) for full schema overview and non-Supabase setup

## CI Requirements

All PRs must pass these checks before merging:

| Check | Command | Job |
|-------|---------|-----|
| Ruff linting | `ruff check .` | `backend` |
| Ruff formatting | `ruff format --check .` | `backend` |
| Type checking (ty) | `ty check` | `backend` |
| Backend tests | `pytest tests/ -v` | `backend` |
| ESLint | `npm run lint` | `frontend` |
| TypeScript + build | `npm run build` | `frontend` |
| Dependency audit | `uv audit` | `security` |
| Python SAST | `bandit -r app/` | `security` |
| Node audit | `npm audit` | `security` |

## Data Pipelines

Pipelines in `backend/app/pipelines/` are idempotent — safe to re-run:

```bash
cd backend

# Seed all curated data + run migrations
uv run python -m app.pipelines.seed_all

# Precompute neighborhood scores (requires backend running on :8000)
uv run python -m app.pipelines.precompute_scores

# Compute builder trust scores
uv run python -m app.pipelines.compute_trust_scores

# Seed curated POIs
uv run python -m app.pipelines.seed_curated_pois
```
