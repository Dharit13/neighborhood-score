# Neighborhood Score — Bangalore

Data-driven neighborhood scoring platform for Bangalore home buyers. Scores 126 neighborhoods across 17 livability dimensions using curated data, PostGIS spatial analysis, and Claude AI verification.

## What It Does

- **17-Dimension Scoring** — safety, walkability, transit, hospitals, schools, air quality, flood risk, water supply, power, noise, commute, builders, affordability, future infra, delivery, business opportunity, cleanliness
- **Property Ad Claim Verification** — paste a property ad, get each distance/time claim truth-checked against Google Maps data
- **AI Neighborhood Recommender** — answer 4 lifestyle questions (budget, commute, priorities, lifestyle) → get 3 best-fit neighborhoods with side-by-side comparison
- **Builder Trust Profiles** — RERA compliance, delivery track record, NCLT proceedings, consumer court cases, trust scores
- **Area Intelligence** — infrastructure timelines, pricing trends, nearby builders
- **AI Chat & Reports** — Claude-powered conversational Q&A and downloadable PDF reports

## Scoring Dimensions

| Dimension | Weight | Data Source |
|-----------|--------|-------------|
| Safety | 14% | Karnataka Crime Data, BBMP CCTV/streetlights, police stations |
| Walkability | 9% | OSM Overpass (NEWS-India framework) |
| Transit Access | 9% | Metro/bus/train stations (MOHUA TOD norms) |
| Commute | 8% | Google Distance Matrix (peak/off-peak to tech parks) |
| Flood Risk | 8% | BBMP flood spots, elevation, drainage (data.opencity.in, KSRSAC) |
| Air Quality | 8% | CPCB AQI stations (IDW interpolation) |
| Hospital Access | 7% | NABH hospitals, bed density, emergency access |
| Water Supply | 7% | BWSSB stage classification |
| School Access | 6% | RTE norms, ranked schools (Times Now, IIRF 2024) |
| Affordability | 5% | EMI-to-income ratio (99acres, MagicBricks) |
| Noise | 4% | Airport flight paths, highways, construction (CPCB, DGCA) |
| Power Reliability | 4% | BESCOM tier classification |
| Future Infrastructure | 4% | Metro/road project proximity + completion timelines |
| Cleanliness | 3% | Slum proximity, waste infrastructure (data.opencity.in) |
| Builder Reputation | 3% | RERA Karnataka, delivery ratings |
| Delivery Coverage | 0.5% | Swiggy/Zepto/Blinkit/BigBasket serviceability |
| Business Opportunity | 0.5% | Startup density, commercial rent, footfall |

## Quick Start

### Prerequisites

| Key | Required | Get it from |
|-----|----------|-------------|
| **Google Maps API Key** | Yes | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — enable Maps JavaScript, Geocoding, Directions, and Places APIs |
| **Anthropic API Key** | Yes (for AI features) | [Anthropic Console](https://console.anthropic.com/) |
| **Supabase / PostgreSQL** | Yes | [Supabase](https://supabase.com/) — create a project with PostGIS enabled |

### Setup

```bash
# 1. Clone the repo
git clone https://github.com/dhshah/raorpay.git
cd raorpay

# 2. Configure environment
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Edit both .env files with your API keys

# 3. Install dependencies
make install-dev

# 4. Set up the database
# Run migrations in your Supabase SQL editor (in order):
#   backend/supabase/migrations/001_create_tables.sql
#   backend/supabase/migrations/002_create_indexes.sql
#   backend/supabase/migrations/003_add_cleanliness.sql
#   backend/supabase/migrations/004_add_ward_mapping.sql
#   backend/supabase/migrations/005_google_places.sql
#   backend/supabase/migrations/006_property_intelligence.sql

# 5. Seed data
cd backend
uv run python -m app.pipelines.seed_all
cd ..

# 6. Precompute scores (requires backend running)
make dev-backend &
cd backend && uv run python -m app.pipelines.precompute_scores
cd ..

# 7. Start development
make dev-backend    # terminal 1
make dev-frontend   # terminal 2
```

### Quality Checks

```bash
make check          # lint + typecheck + test + security
make format         # auto-format backend
make test           # backend tests only
make security       # dependency audit + SAST
```

## API

### Core Scoring
```
POST /api/scores           — Full 17-dimension score for a neighborhood
GET  /api/prefetch         — All neighborhood pins for map
GET  /api/neighborhoods    — Neighborhood name list
```

### Claim Verification
```
POST /api/verify-claims    — Truth-check property ad claims
```

### AI Features
```
POST /api/ai-chat          — Claude streaming chat (SSE)
POST /api/generate-report  — Claude PDF report data
POST /api/ai-recommend     — AI neighborhood recommendations
```

### Property Intelligence
```
GET  /api/builders         — List builders by area/tier/segment
GET  /api/builder/{slug}   — Full builder profile
GET  /api/area/{slug}      — Area intelligence
POST /api/intelligence-brief — AI buyer advisory
GET  /api/search           — Global search
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database | PostgreSQL + PostGIS (Supabase) |
| Auth | Supabase Auth (email/password + Google OAuth) |
| AI | Anthropic Claude (chat, reports, verification, recommendations) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |
| Charts | Recharts |
| Maps | Google Maps JavaScript API |
| CI | GitHub Actions |

### Why Anthropic SDK directly (not LiteLLM)?

This project uses the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) directly instead of wrapper libraries like LiteLLM. In March 2026, LiteLLM was hit by a [supply chain attack](https://www.bleepingcomputer.com/news/security/popular-litellm-pypi-package-compromised-in-teampcp-supply-chain-attack/) — backdoored versions on PyPI stole credentials, SSH keys, and cloud tokens from millions of installs. LiteLLM sits between your app and every LLM provider's API keys, making it a high-value target.

Using the official SDK directly means fewer dependencies, a smaller attack surface, and no single package that holds all your secrets. Security over convenience.

## Security

This project takes a security-first approach — minimal dependencies, automated scanning, and no wrapper libraries that aggregate API keys.

### Automated Scanning

| Tool | What it does | Runs in |
|------|-------------|---------|
| **Dependabot** | Auto-creates PRs for vulnerable dependencies (Python, npm, GitHub Actions) | GitHub (weekly) |
| **`uv audit`** | Scans Python dependencies against the OSV vulnerability database | CI + `make security` |
| **Bandit** | Python SAST — SQL injection, hardcoded secrets, shell injection, insecure functions | CI + `make security` |
| **`npm audit`** | Scans Node dependencies against the GitHub Advisory Database | CI + `make security` |

```bash
make security    # run all security checks locally
make check       # lint + typecheck + test + security
```

### Supply Chain Philosophy

- **Direct SDK only** — uses the official [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python), not wrapper libraries like LiteLLM (see [why](#why-anthropic-sdk-directly-not-litellm) above)
- **Minimal dependencies** — fewer packages = smaller attack surface
- **Pinned CI actions** — GitHub Actions pinned to specific versions via Dependabot
- **No secrets in code** — all credentials via environment variables, `.env` files gitignored

See [SECURITY.md](SECURITY.md) for vulnerability reporting policy.

## Data Sources & Attribution

- **OpenStreetMap**: ODbL license — amenities, road networks, transit
- **data.opencity.in**: CC BY 4.0 — crime data, police stations, streetlights, hospitals, schools, metro stations
- **openbangalore GitHub**: Open data — BMTC bus stops, schools, police stations
- **NABH (portal.nabh.co)**: Public accreditation directory
- **Karnataka RERA (rera.karnataka.gov.in)**: Public builder/project complaints
- **CPCB**: Air quality monitoring data
- **BBMP**: Flood risk, waste infrastructure, ward data
- **KSRSAC**: Elevation and terrain data
- **Times Now / IIRF 2024**: School rankings
- **99acres / MagicBricks**: Property pricing data

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, PR rules, and how to add new scoring dimensions.

## License

[MIT](LICENSE)
