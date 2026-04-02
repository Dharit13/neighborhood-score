# Development Guide

Welcome to Neighborhood Score development! This guide covers everything you need to know about contributing scorers, data, pipelines, and other improvements to the platform.

## Getting Started

### Development Setup

1. **Clone the Repository**

```bash
git clone https://github.com/Dharit13/neighborhood-score.git
cd neighborhood-score
```

2. **Install uv** (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with Homebrew
brew install uv
```

3. **Install Dependencies**

```bash
# Install all dependencies (backend + frontend)
make install-dev

# Configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit both .env files with your own API keys
```

4. **Verify Installation**

```bash
# Run all checks to ensure everything works
make check    # lint + typecheck + test + security
```

### Development Environment

The `make install-dev` command installs:

- **Backend**: Python 3.12 dependencies via `uv sync --group dev` — includes FastAPI, asyncpg, ruff, ty, pytest, bandit
- **Frontend**: Node.js 20 dependencies via `npm ci` — includes React 19, TypeScript, Vite, Tailwind CSS 4, ESLint

### Required API Keys

| Key | Required For | Get It From |
|-----|-------------|-------------|
| **Google Maps API Key** | Maps, geocoding, commute data | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — enable Maps JavaScript, Geocoding, Directions, Distance Matrix, and Places APIs |
| **Anthropic API Key** | AI chat, reports, recommendations, verification | [Anthropic Console](https://console.anthropic.com/) |
| **Supabase / PostgreSQL** | Database | [Supabase](https://supabase.com/) or any PostgreSQL with PostGIS (see [DATABASE.md](../DATABASE.md)) |

## Architecture Overview

### Data Flow

```
Curated JSON files ──→ Seed Pipelines ──→ PostgreSQL/PostGIS
                                              │
External APIs ──────→ Fetch Pipelines ────────┘
(OpenCity, BBMP,                              │
 Google Maps,                                 ▼
 CPCB, RERA)                        ┌─────────────────┐
                                    │  17 Scorers      │
                                    │  (per dimension)  │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
           precompute_scores.py      POST /api/scores         verify_ai.py
           (batch → JSON cache)      (live computation)       (Claude → DB)
                    │                        │                        │
                    ▼                        ▼                        ▼
           precomputed_scores.json   API Response              neighborhood_verification
                    │                        │                        │
                    └────────────┬───────────┘────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │     React Frontend   │
                    │  Map + Sidebar + AI  │
                    └─────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL + PostGIS (Supabase) |
| **DB Drivers** | asyncpg (API), psycopg2 (pipelines) |
| **AI** | Anthropic Claude SDK (direct — no LiteLLM or wrappers) |
| **Auth** | Supabase Auth (email/password + Google OAuth), ES256 JWT verification |
| **Frontend** | React 19, TypeScript 5.9, Vite 8 |
| **Styling** | Tailwind CSS 4, Framer Motion |
| **Maps** | Google Maps JavaScript API |
| **Charts** | Recharts |
| **CI/CD** | GitHub Actions (lint + typecheck + test + security) |
| **Security** | uv audit, Bandit (SAST), npm audit, Dependabot |

## Contributing Scorers

Scorers are the core computation units. Each one computes a 0-100 score for a neighborhood dimension.

### Scorer Structure

All 17 scorers live in `backend/app/scorers/` and follow the same pattern:

```python
# backend/app/scorers/your_dimension.py

import asyncpg

from app.models import ScoreResult


async def compute(lat: float, lon: float, conn: asyncpg.Connection) -> ScoreResult:
    """Compute your_dimension score for the given coordinates.

    Parameters
    ----------
    lat : float
        Latitude of the neighborhood center
    lon : float
        Longitude of the neighborhood center
    conn : asyncpg.Connection
        Database connection from the asyncpg pool

    Returns
    -------
    ScoreResult
        Score (0-100), label, details dict, breakdown list, and sources list
    """
    # 1. Query pre-seeded data from PostGIS tables
    row = await conn.fetchrow(
        """
        SELECT score, metric_1, metric_2
        FROM your_dimension_zones
        ORDER BY center_geog <-> ST_MakePoint($2, $1)::geography
        LIMIT 1
        """,
        lat, lon
    )

    if not row:
        # Conservative default when no data available
        return ScoreResult(
            score=50,
            label="Average",
            details={"data_confidence": "low"},
            breakdown=[],
            sources=["No data available for this area"]
        )

    # 2. Compute score (always 0-100)
    score = _calculate_score(row)
    score = max(0, min(100, score))  # Clamp to bounds

    # 3. Return structured result
    return ScoreResult(
        score=round(score, 1),
        label=_get_label(score),
        details={
            "metric_1": row["metric_1"],
            "metric_2": row["metric_2"],
        },
        breakdown=[
            {"factor": "Metric 1", "value": row["metric_1"], "weight": 0.6},
            {"factor": "Metric 2", "value": row["metric_2"], "weight": 0.4},
        ],
        sources=["Source 1", "Source 2"]
    )
```

### Key Requirements

- **Score range**: Always return 0-100. Clamp with `max(0, min(100, score))`.
- **Async**: All scorers must be `async def`.
- **Parameterized SQL**: Always use `$1`, `$2` placeholders — never f-strings or `.format()`.
- **PostGIS proximity**: Use `ORDER BY geog <-> ST_MakePoint($2, $1)::geography LIMIT 1` for nearest-neighbor queries. Note: PostGIS expects `(longitude, latitude)` order.
- **Missing data**: Return a conservative default (40-70) with `data_confidence: "low"` when no data exists.
- **Sources**: Always include data source attribution in the `sources` list.

### Adding a New Scoring Dimension

1. **Create the scorer** in `backend/app/scorers/your_dimension.py`
2. **Add curated data** in `backend/app/data/curated/your_data.json`
3. **Add a seed pipeline** in `backend/app/pipelines/seed_your_data.py`
4. **Add the weight** to `SCORE_WEIGHTS` in `backend/app/config.py` — all weights must sum to 1.0
5. **Wire it into scoring** in `backend/app/routers/scores.py` — add to the `asyncio.gather` call
6. **Add a frontend card** in `frontend/src/components/`
7. **Add a migration** if new DB tables are needed in `backend/supabase/migrations/`
8. **Run `make check`** to verify everything passes

### Testing Scorers

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
        print(f"Score: {result.score}, Label: {result.label}")
        print(f"Details: {result.details}")

asyncio.run(test())
```

### Existing Scorer Enhancement Ideas

Each scorer in `backend/app/scorers/` can be improved:

| Scorer | Current Approach | Enhancement Ideas |
|--------|-----------------|-------------------|
| `safety.py` | Crime rate + police proximity | Add CCTV density, street lighting coverage |
| `air_quality.py` | CPCB station IDW interpolation | Integrate SAFAR or PurpleAir sensors |
| `flood_risk.py` | BBMP spots + elevation | Add monsoon seasonal variation |
| `commute.py` | Google Distance Matrix to tech parks | Add time-of-day granularity |
| `walkability.py` | NEWS-India framework zones | Increase coverage beyond 33 zones |
| `water.py` | BWSSB stage mapping | Add borewell/tanker dependency data |

## Contributing Data

### Curated Data Files

The easiest way to contribute — JSON files in `backend/app/data/curated/`:

| File | Contents | How to Improve |
|------|----------|----------------|
| `safety_zones.json` | Crime rates, police station coverage | Add missing stations, update NCRB/KSP stats |
| `water_zones.json` | BWSSB stage classifications | Update supply schedules |
| `power_zones.json` | BESCOM tier ratings | Add recent outage data |
| `property_prices.json` | Avg price/sqft, rent, YoY growth | Update with latest RERA/ANAROCK data |
| `walkability_zones.json` | Footpath quality, lighting | Ground-truth from walking audits |
| `top_schools.json` | CBSE/ICSE/State board schools | Add missing schools, update ratings |
| `nabh_hospitals.json` | NABH-accredited hospitals | Add clinics, ambulance response times |
| `metro_stations.json` | Namma Metro stations | Add Phase 2/3 stations as they open |
| `bus_stops.json` | BMTC bus stop locations | Add missing stops, route frequency |
| `aqi_stations.json` | CPCB air quality stations | Add seasonal AQI patterns |
| `future_infra.json` | Upcoming infrastructure projects | Timeline updates, new projects |
| `builders.json` | Builder profiles, RERA compliance | Add reviews, delivery track records |
| `areas.json` | Area boundaries and metadata | Sub-locality boundaries, pin codes |

**Rules for data contributions:**

- Keep the existing JSON schema — add entries, don't change structure
- Include your data source in the PR description
- Run `make check` to ensure nothing breaks

### Seed Pipelines

Pipelines in `backend/app/pipelines/` are idempotent — they use `INSERT ... ON CONFLICT` to upsert:

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

# Individual seeds
uv run python -m app.pipelines.seed_neighborhoods
uv run python -m app.pipelines.seed_zones
uv run python -m app.pipelines.seed_prices
uv run python -m app.pipelines.seed_transit
uv run python -m app.pipelines.seed_points
uv run python -m app.pipelines.seed_infra
```

## Contributing Frontend

### Stack

- **React 19** with TypeScript
- **Tailwind CSS 4** utility classes — no custom CSS unless absolutely necessary
- **Recharts** for data visualization
- **Google Maps JavaScript API** for map rendering
- **Framer Motion** for animations
- **Fetch API** with `/api/` prefix — Vite proxies to backend on `:8000`
- **No external state management** — React hooks only

### Frontend Modes

| Mode | Tab | Feature |
|------|-----|---------|
| Explore | Compass | Map + sidebar — click pins for full 17-dimension scores |
| Compare | MapPin | AI recommender — 4 lifestyle questions → top 3 neighborhoods |
| Verify | Shield | Claim checker — paste property ad, get truth-checked claims |
| Sources | Database | Methodology, data sources, freshness metadata |

### Key Components

| Component | Purpose |
|-----------|---------|
| `Map.tsx` | Google Map with neighborhood pins (color-coded by score) |
| `MapSidebar.tsx` | Score details sidebar with dimension cards |
| `ScoreCard.tsx` | Individual dimension score card |
| `CompareMode.tsx` | AI recommender with 4-step questionnaire |
| `VerifyClaims.tsx` | Property ad claim verification |
| `PropertyIntelligencePanel.tsx` | Builders, area intel, AI brief (tabbed) |
| `BuilderCard.tsx` | 3D builder card with trust tier + metrics |
| `LandingHero.tsx` | Hero section with 3D mouse-tracking parallax |
| `LoginPage.tsx` | City selection + auth (email/Google) |

### Frontend Contribution Checklist

- [ ] TypeScript types correct (`npx tsc -b --noEmit`)
- [ ] ESLint passes (`npm run lint`)
- [ ] Uses Tailwind CSS utility classes
- [ ] API calls use `/api/` prefix
- [ ] Mobile responsive
- [ ] No external state management libraries added

## Development Tools and Standards

### Linting and Formatting

```bash
# Run everything
make check          # lint + typecheck + test + security

# Backend
cd backend
uv run ruff check .           # Lint
uv run ruff format .          # Format
uv run ruff check --fix .     # Lint with auto-fix
uv run ty check               # Type check (Python 3.12)

# Frontend
cd frontend
npm run lint                  # ESLint
npx tsc -b --noEmit           # TypeScript type check
```

### Ruff Configuration

Configured in `backend/pyproject.toml`:

- **Target**: Python 3.12
- **Line length**: 120
- **Rules**: E (pycodestyle errors), F (pyflakes), I (isort), UP (pyupgrade)
- **Ignores**: E501 (line too long — handled by formatter)

### ty Configuration

Type checker configured in `backend/pyproject.toml`:

- **Python version**: 3.12
- **Warnings** (not errors): `unresolved-attribute`, `no-matching-overload` — needed for Anthropic SDK union types

### Testing

```bash
# All tests
make test

# Backend
cd backend && uv run pytest tests/ -v

# Specific tests
cd backend && uv run pytest tests/test_api.py -v
cd backend && uv run pytest -k "test_scores"

# Frontend
cd frontend && npx vitest run
```

**Backend testing patterns:**

- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`
- Database pool is mocked — tests don't need a real database
- Auth is mocked via `app.dependency_overrides[require_auth]`
- Test files: `test_api.py` (endpoints), `test_config.py` (configuration), `test_geo.py` (geospatial), `test_models.py` (Pydantic models)

### Security Checks

```bash
make security

# Individual tools
cd backend && uv audit                                  # Python dep audit (OSV database)
cd backend && uv run bandit -r app/ -c pyproject.toml   # Python SAST
cd frontend && npm audit --audit-level=high             # Node dep audit
```

**Bandit skips** (configured in `pyproject.toml`):

| Skip | Reason |
|------|--------|
| B101 | `assert` used for dev guards |
| B110 | `try/except/pass` for best-effort parsing |
| B310 | `urllib.urlopen` with controlled URLs only |
| B405/B314 | XML parsing — no untrusted XML input |
| B608 | SQL injection — all flagged queries use parameterized placeholders |

## Git Workflow

### Branch Naming

- `feature/scorer-name` — New scoring dimensions
- `feature/description` — New features
- `data/source-description` — Data improvements
- `fix/issue-description` — Bug fixes
- `docs/section-updates` — Documentation updates

### Commit Messages

Imperative mood, concise subject line (<72 chars):

```
Add flood risk scorer with BBMP ward data
Fix transit score calculation for multi-modal bonus
Update metro stations with Phase 2A data
```

### Pull Request Process

1. Create feature branch from `master`
2. Implement changes with tests
3. Run `make check` locally
4. Create PR with clear description — explain what, why, and how
5. Fill out the PR template
6. At least **1 maintainer approval** required
7. CI must pass (backend + frontend jobs)
8. **Squash merge** preferred

## CI Requirements

All PRs must pass before merging:

| Check | Command | CI Job |
|-------|---------|--------|
| Ruff linting | `ruff check .` | `backend` |
| Ruff formatting | `ruff format --check .` | `backend` |
| Type checking (ty) | `ty check` | `backend` |
| Backend tests | `pytest tests/ -v` | `backend` |
| ESLint | `npm run lint` | `frontend` |
| TypeScript + build | `npm run build` | `frontend` |
| Dependency audit | `uv audit` | `security` |
| Python SAST | `bandit -r app/` | `security` |
| Node audit | `npm audit` | `security` |

## Database

### Schema Overview

33 PostGIS-enabled tables across scoring, property intelligence, and infrastructure. Key tables:

| Table | Rows | Purpose |
|-------|------|---------|
| `neighborhoods` | 126 | Canonical neighborhoods with PostGIS center coordinates |
| `safety_zones` | 126 | Crime, CCTV, streetlight, police metrics |
| `property_prices` | 126 | Price/rent/affordability per neighborhood |
| `pois` | 25,000+ | Points of interest (hospitals, schools) from Google Places |
| `commute_times` | 5,200 | Driving times to 10 tech parks (4 modes each) |
| `slum_zones` | 11,000+ | Slum polygons for cleanliness scoring |
| `metro_stations` | 109 | Namma Metro stations (operational + planned) |
| `flood_risk` | 126 | Flood risk per neighborhood |
| `noise_zones` | 126 | Noise exposure estimates |
| `delivery_coverage` | 126 | Quick-commerce serviceability |
| `builders` | 25 | Builder profiles with trust scores |
| `neighborhood_verification` | 126 | Claude AI verification results |

### Migrations

6 SQL migration files in `backend/supabase/migrations/` — run in order:

```
001_create_tables.sql        # Core tables (neighborhoods, zones, prices, transit)
002_create_indexes.sql       # PostGIS spatial indexes
003_add_cleanliness.sql      # Slum zones, waste infrastructure
004_add_ward_mapping.sql     # BBMP ward boundaries
005_google_places.sql        # POIs table for Google Places data
006_property_intelligence.sql # Builders, areas, infrastructure, landmarks
```

For non-Supabase PostgreSQL setup, see [DATABASE.md](../DATABASE.md).

## Caching Strategy

1. **Precomputed scores** — Full API responses for all neighborhoods, generated via `precompute_scores.py`, loaded into memory at server startup
2. **Score cache lookup** — `POST /api/scores` checks in-memory cache by name or proximity (<1km). Hit = <100ms, miss = ~13s live computation
3. **Prefetch cache** — `GET /api/prefetch` serves pin data from precomputed scores
4. **AI verification** — Stored in `neighborhood_verification` DB table after one-time Claude batch run
5. **Frontend default** — `defaultScores.json` bundled at build time for instant sidebar load

## Security

### Rules

- Never commit `.env` files or credentials
- Never add LiteLLM or similar API key aggregation libraries (supply chain risk — [March 2026 attack](https://www.bleepingcomputer.com/news/security/popular-litellm-pypi-package-compromised-in-teampcp-supply-chain-attack/))
- All new dependencies must pass `uv audit` / `npm audit`
- Parameterized SQL everywhere — no f-strings or `.format()` in queries
- API keys are server-side only — never expose to frontend except via `/api/config/map`
- JWT auth uses ES256 (Supabase ECC P-256 signing key)

### Automated Scanning

| Tool | What It Does | Runs In |
|------|-------------|---------|
| **Dependabot** | Auto-creates PRs for vulnerable dependencies | GitHub (weekly) |
| **`uv audit`** | Scans Python deps against OSV database | CI + `make security` |
| **Bandit** | Python SAST (SQL injection, hardcoded secrets, shell injection) | CI + `make security` |
| **`npm audit`** | Scans Node deps against GitHub Advisory Database | CI + `make security` |

## Debugging Guide

### Backend

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ConnectionRefusedError` on startup | Database not reachable | Check `DB_HOST`, `DB_PORT`, `DB_PASSWORD` in `.env` |
| `Could not geocode address` | Google Maps API issue | Verify `GOOGLE_MAPS_API_KEY` has Geocoding API enabled |
| Scorer returns `None` or score is 0 | Empty database table | Run `uv run python -m app.pipelines.seed_all` |
| `ANTHROPIC_API_KEY not set` warning | Missing env var | Add key to `.env` |
| `429 Too Many Requests` | Rate limiter triggered | Wait 2-5 seconds and retry |

### Frontend

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Map shows gray/blank | Missing Google Maps key | Backend must be running — frontend gets key from `/api/config/map` |
| CORS errors in console | Backend not running | Start backend on `:8000` — Vite proxies `/api` there |
| Login redirects fail | Supabase URL/key mismatch | Check `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` in `frontend/.env` |
| Scores show as 0 | Precomputed scores not generated | Run `precompute_scores` pipeline |
| Build fails with type errors | TypeScript strict mode | Run `npx tsc -b --noEmit` to see all errors |

## Documentation

| File | Purpose |
|------|---------|
| [README.md](../README.md) | Project overview, quick start, API reference |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | PR rules, contribution checklist |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Full system architecture, database schema, data flows |
| [METHODOLOGY.md](../METHODOLOGY.md) | Scoring algorithms, weight selection, data sources |
| [DATABASE.md](../DATABASE.md) | Non-Supabase PostgreSQL setup guide |
| [SECURITY.md](../SECURITY.md) | Vulnerability reporting policy |
| [docs/decisions/](decisions/) | Architecture decision records (ADRs) |

## Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [001](decisions/001-scoring-dimensions-and-weights.md) | 17 scoring dimensions with ANAROCK-based weights |
| [002](decisions/002-postgis-spatial-analysis.md) | PostGIS for spatial analysis over application-level math |
| [003](decisions/003-direct-anthropic-sdk.md) | Direct Anthropic SDK over LiteLLM (supply chain security) |
| [004](decisions/004-missing-data-handling.md) | Conservative defaults for missing data (no interpolation) |
