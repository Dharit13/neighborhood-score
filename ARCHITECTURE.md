# Neighborhood Score — Architecture

> Data-driven neighborhood scoring platform for Bangalore home buyers. Scores 130+ neighborhoods across 17 livability dimensions using curated data, PostGIS spatial analysis, and Claude AI verification.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL + PostGIS (Supabase) |
| **DB Drivers** | asyncpg (API), psycopg2 (pipelines) |
| **AI** | Anthropic Claude (verification + chat + reports + recommendations) |
| **Auth** | Supabase Auth (email/password + Google OAuth) |
| **Frontend** | React 19, TypeScript 5.9, Vite 8 |
| **Styling** | Tailwind CSS 4, Framer Motion |
| **Maps** | Google Maps JavaScript API |
| **PDF** | jsPDF (client-side report generation) |
| **Charts** | Recharts |
| **Build** | Makefile, uv (Python), npm (frontend) |
| **CI/CD** | GitHub Actions (lint + typecheck + test + security) |
| **Testing** | pytest (backend), ruff + ty (static analysis) |
| **Security** | uv audit, Bandit (SAST), npm audit, Dependabot |

---

## Repository Structure

```
raorpay/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry, CORS, lifespan
│   │   ├── config.py            # Constants, SCORE_WEIGHTS, paths
│   │   ├── db.py                # asyncpg pool + psycopg2 helpers
│   │   ├── models.py            # Pydantic models (request/response)
│   │   ├── routers/
│   │   │   ├── scores.py        # Core scoring API + prefetch + cache + AI recommend
│   │   │   ├── ai_chat.py       # Claude streaming chat
│   │   │   ├── report.py        # Claude report generation
│   │   │   └── property_intelligence.py  # Builders, areas, search, intel brief
│   │   ├── scorers/             # 17 dimension scorers
│   │   │   ├── walkability.py
│   │   │   ├── safety.py
│   │   │   ├── hospital.py
│   │   │   ├── school.py
│   │   │   ├── transit.py
│   │   │   ├── builder.py
│   │   │   ├── air_quality.py
│   │   │   ├── water_supply.py
│   │   │   ├── power.py
│   │   │   ├── future_infra.py
│   │   │   ├── property_price.py
│   │   │   ├── flood_risk.py
│   │   │   ├── commute.py
│   │   │   ├── delivery_coverage.py
│   │   │   ├── noise.py
│   │   │   ├── business_opportunity.py
│   │   │   └── cleanliness.py
│   │   ├── pipelines/           # Data ingestion + processing
│   │   │   ├── seed_all.py      # Full orchestration
│   │   │   ├── runner.py        # CLI runner
│   │   │   ├── seed_neighborhoods.py
│   │   │   ├── seed_zones.py
│   │   │   ├── seed_prices.py
│   │   │   ├── seed_transit.py
│   │   │   ├── seed_points.py
│   │   │   ├── seed_infra.py
│   │   │   ├── seed_curated_pois.py
│   │   │   ├── seed_areas.py         # Area metadata
│   │   │   ├── seed_landmarks.py     # Landmark registry
│   │   │   ├── seed_infrastructure.py # Infra projects + timelines
│   │   │   ├── fetch_*.py            # 16 external data fetchers
│   │   │   ├── scrape_krera.py       # RERA data scraping
│   │   │   ├── scrape_sitesetu.py    # Builder data source
│   │   │   ├── fetch_reviews.py      # Google reviews sentiment
│   │   │   ├── fetch_compdata.py     # Company data (CIN, NCLT, directors)
│   │   │   ├── compute_trust_scores.py   # Multi-factor builder trust rating
│   │   │   ├── enrich_builders_offline.py # Builder enrichment
│   │   │   ├── precompute_scores.py  # Batch score caching
│   │   │   └── verify_ai.py     # Claude AI verification
│   │   ├── lib/
│   │   │   ├── claim_parser.py      # Extract claims from property ads
│   │   │   ├── commute_verifier.py  # Verify commute times vs Google Maps
│   │   │   └── landmark_resolver.py # Fuzzy-match landmarks/destinations
│   │   ├── utils/
│   │   │   ├── geo.py           # Geocoding, haversine, walk time
│   │   │   └── overpass.py      # OSM Overpass API client
│   │   └── data/curated/        # 16 curated JSON data files
│   ├── tests/                   # pytest test suite
│   │   ├── test_api.py          # API endpoint tests
│   │   ├── test_config.py       # Configuration tests
│   │   ├── test_geo.py          # Geospatial utility tests
│   │   └── test_models.py       # Pydantic model tests
│   ├── supabase/migrations/     # 6 SQL migration files
│   └── pyproject.toml
│
└── frontend/
    ├── src/
    │   ├── main.tsx             # React entry
    │   ├── App.tsx              # Main shell: modes, search, prefetch
    │   ├── types.ts             # TypeScript API types
    │   ├── index.css            # Tailwind + theme
    │   ├── data/
    │   │   └── defaultScores.json  # Bundled default for instant load
    │   ├── contexts/
    │   │   └── AuthContext.tsx  # Supabase auth (email + Google OAuth)
    │   ├── components/
    │   │   ├── Map.tsx          # Google Map + neighborhood pins
    │   │   ├── MapSidebar.tsx   # Score details sidebar
    │   │   ├── ScoreCard.tsx    # Individual dimension card
    │   │   ├── ScoreRing.tsx    # Animated score ring
    │   │   ├── CompareMode.tsx  # AI-powered neighborhood recommender (4-step questionnaire → 3-way comparison)
    │   │   ├── VerifyClaims.tsx # Ad claim verification
    │   │   ├── DataSources.tsx  # Methodology & sources
    │   │   ├── PropertyIntelligencePanel.tsx  # Builders, area intel, claims, AI brief (tabbed)
    │   │   ├── BuilderCard.tsx  # 3D builder card with trust tier + metrics
    │   │   ├── TrustScoreCircle.tsx   # Animated circular trust score
    │   │   ├── TrustBreakdownChart.tsx # Trust factor breakdown
    │   │   ├── InfraTimeline.tsx       # Infrastructure project timeline
    │   │   ├── ClaimCard.tsx    # Individual claim verification card
    │   │   ├── MetricCard.tsx   # Area intelligence metric card
    │   │   ├── RedFlagAlert.tsx # Severity-based risk alerts
    │   │   ├── SearchAutocomplete.tsx  # Global search (builders/areas/landmarks)
    │   │   ├── LandingHero.tsx  # Hero section with 3D mouse tracking
    │   │   ├── LoginPage.tsx    # City selection + auth (email/Google)
    │   │   ├── CategoryChips.tsx
    │   │   ├── NeighborhoodInput.tsx
    │   │   ├── ScrollReveal3D.tsx      # Scroll-triggered 3D reveal
    │   │   ├── Section3DHeading.tsx    # 3D section headings
    │   │   ├── Perspective3DContainer.tsx # 3D perspective wrapper
    │   │   ├── ui/             # UI primitives (badge, button, beams-background, ai-input, etc.)
    │   │   └── kokonutui/      # Glass card components
    │   ├── hooks/
    │   │   └── use3DMouseTrack.ts  # 3D parallax mouse tracking
    │   ├── utils/
    │   │   ├── generateReport.ts
    │   │   ├── generateComprehensiveReport.ts
    │   │   ├── freshnessMap.ts
    │   │   ├── trustTiers.ts   # Trust tier colors/labels
    │   │   └── categories.ts
    │   └── lib/
    │       ├── utils.ts        # cn() helper
    │       └── supabase.ts     # Supabase client init
    ├── vite.config.ts
    ├── package.json
    └── tsconfig*.json
```

---

## Data Flow

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
           precomputed_scores.json   NeighborhoodScoreResponse  neighborhood_verification
                    │                        │                        │
                    └────────────┬───────────┘────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │   GET /api/prefetch  │ ←── map pins (instant)
                    │  POST /api/scores   │ ←── sidebar (cached or live)
                    └────────┬────────────┘
                             │
                             ▼
                    ┌─────────────────────┐
                    │     React Frontend   │
                    │  Map + Sidebar + AI  │
                    └─────────────────────┘
```

### AI Recommendation Flow
```
User answers 4 questions (budget, commute, priorities, lifestyle)
        │
        ▼
POST /api/ai-recommend
        │
        ├── Phase 1: Pre-filter from _score_cache (74 neighborhoods)
        │             Filter by budget → rank by priority-weighted scores → top 8
        │
        ├── Phase 2: Claude picks top 3 with reason + highlights (structured JSON)
        │
        └── Phase 3: Attach full NeighborhoodScoreResponse from cache
                │
                ▼
        3-way comparison (radar chart + score table + AI cards)
```

### Claim Verification Flow
```
User pastes property ad text
        │
        ▼
POST /api/verify-claims
        │
        ├── claim_parser.py → extract distance/time claims from text
        │
        ├── landmark_resolver.py → fuzzy-match destinations
        │
        ├── commute_verifier.py → Google Maps Distance Matrix for actual times
        │
        └── Verdict per claim (ACCURATE / SLIGHTLY_OPTIMISTIC / MISLEADING)
                │
                ▼
        ClaimCards with color-coded verdicts + narrative summary
```

---

## API Endpoints

| Method | Path | Purpose | Response Time |
|--------|------|---------|---------------|
| **Core Scoring** | | | |
| GET | `/api/prefetch` | All neighborhood pins for map | <100ms (cached) |
| POST | `/api/scores` | Full 17-dimension score | <100ms (cached) / ~13s (live) |
| GET | `/api/neighborhoods` | Neighborhood name list | <200ms |
| GET | `/api/config/map` | Google Maps API key | <50ms |
| GET | `/api/health` | Health check | <50ms |
| GET | `/api/data-freshness` | Data freshness metadata | <200ms |
| **Claim Verification** | | | |
| POST | `/api/verify-claims` | Verify property ad claims | ~2s |
| POST | `/api/commute/refresh` | Live Google commute data | ~5s |
| POST | `/api/transit/walk` | Live walking directions | ~3s |
| **AI Features** | | | |
| POST | `/api/ai-chat` | Claude streaming chat | SSE stream |
| POST | `/api/generate-report` | Claude PDF report data | ~10s |
| POST | `/api/ai-recommend` | AI neighborhood recommendations (lifestyle Q&A → top 3) | ~2s |
| **Property Intelligence** | | | |
| GET | `/api/builders` | List builders by area/tier/segment with AI summaries | <200ms |
| GET | `/api/builder/{slug}` | Full builder profile (trust, NCLT, risk flags) | <200ms |
| GET | `/api/area/{slug}` | Area intelligence (builders, infra, pricing) | <200ms |
| POST | `/api/intelligence-brief` | AI-generated buyer advisory for address | ~3s |
| GET | `/api/infrastructure` | Infrastructure projects with timelines | <200ms |
| GET | `/api/search` | Global search (builders, projects, areas, landmarks) | <200ms |

---

## 17 Scoring Dimensions

Each dimension produces a score from 0-100 with label, details, breakdown, and sources.

| Dimension | Weight | Methodology | Data Source |
|-----------|--------|-------------|-------------|
| Safety | 14% | Crime rate + CCTV + streetlights + police density | Karnataka Crime Data, BBMP |
| Walkability | 9% | NEWS-India framework, pedestrian infrastructure | OSM, curated zones |
| Transit Access | 9% | MOHUA TOD norms (500m/800m/2000m) | Metro/bus/train stations |
| Commute | 8% | Google Distance Matrix, peak/off-peak to tech parks | Google Maps API |
| Flood Risk | 8% | BBMP flood spots + elevation + drainage | data.opencity.in, KSRSAC |
| Air Quality | 8% | CPCB AQI, IDW from nearest stations | CPCB monitoring stations |
| Hospital Access | 7% | NABH proximity + bed density + emergency | POIs (Google Places) |
| Water Supply | 7% | BWSSB stage classification | Curated zone data |
| School Access | 6% | RTE norms (1km/3km) + quality + diversity | POIs + curated rankings |
| Affordability | 5% | EMI-to-income ratio at 8% p.a. | 99acres, MagicBricks |
| Noise | 4% | Airport path + highway + construction zones | CPCB, DGCA |
| Power Reliability | 4% | BESCOM tier classification | Curated zone data |
| Future Infrastructure | 4% | Metro/road project proximity + completion | Curated project data |
| Cleanliness | 3% | Slum proximity + waste infrastructure | data.opencity.in |
| Builder Reputation | 3% | RERA compliance + delivery + ratings | RERA Karnataka |
| Delivery Coverage | 0.5% | Swiggy/Zepto/Blinkit/BigBasket serviceability | Public service areas |
| Business Opportunity | 0.5% | Startup density + commercial rent + footfall | Curated zone data |

**Composite formula:** Weighted sum using `SCORE_WEIGHTS` from `config.py`.

---

## Score Labels & Colors

| Score | Label | Pin Color | Use |
|-------|-------|-----------|-----|
| 75+ | Top Notch | Platinum (#c0c7d0) | Map pins, badges |
| 68-75 | Excellent | Blue (#3b82f6) | Map pins, badges |
| 60-68 | Very Good | Green (#2ad587) | Map pins, badges |
| 52-60 | Good | Yellow (#fbbf24) | Map pins, badges |
| <52 | Avoid | Red (#f87171) | Map pins, badges |

**Safety-specific tags:** Woman Safe (90+, pink), Safe (70-90, green), Somewhat Safe (50-70, yellow), Not Safe (<50, red).

---

## Caching Strategy

All data is curated/static — no live data changes between deployments.

1. **Precomputed scores** (`precomputed_scores.json`): Full API responses for all 130 neighborhoods, generated once via `precompute_scores.py`. Loaded into memory at server startup.

2. **Score cache lookup**: `POST /api/scores` checks the in-memory cache by name or proximity (<1km). Cache hit = <100ms response. Cache miss = full scorer computation (~13s).

3. **Prefetch cache**: `GET /api/prefetch` serves pin data from precomputed scores. Cached in memory after first call.

4. **AI verification**: Stored in `neighborhood_verification` DB table after one-time Claude batch run. Read at request time (single DB query, ~50ms).

5. **Frontend default**: `defaultScores.json` bundled at build time for instant sidebar on page load (no API call needed for default neighborhood).

---

## Database Schema (Key Tables)

| Table | Rows | Purpose |
|-------|------|---------|
| `neighborhoods` | 130 | Canonical neighborhoods with PostGIS center coordinates |
| `safety_zones` | 126 | Crime, CCTV, streetlight, police metrics per neighborhood |
| `property_prices` | 126 | Price/rent/affordability per neighborhood |
| `noise_zones` | 130 | Noise estimates per neighborhood |
| `delivery_coverage` | 130 | Quick-commerce serviceability per neighborhood |
| `flood_risk` | 130 | Flood risk assessment per neighborhood |
| `walkability_zones` | 33 | Walkability scores for select neighborhoods |
| `water_zones` | 25 | Water supply stages |
| `power_zones` | 24 | Power reliability tiers |
| `business_opportunity` | 32 | Business metrics per neighborhood |
| `commute_times` | 2400+ | Driving times to 10 tech parks (4 modes each) |
| `pois` | 1000+ | Points of interest (hospitals, schools) |
| `metro_stations` | 70+ | Namma Metro stations |
| `bus_stops` | 400+ | BMTC bus stops |
| `train_stations` | 10+ | Railway stations |
| `tech_parks` | 10 | Major IT parks |
| `builders` | 25 | Builder RERA/reputation data |
| `slum_zones` | 11000+ | Slum polygons for cleanliness scoring |
| `waste_infrastructure` | 358 | BBMP waste facilities |
| `future_infra_projects` | 7 | Planned metro/road projects |
| `future_infra_stations` | 100+ | Stations on planned lines |
| `neighborhood_verification` | 130 | Claude AI verification results |
| `ward_mapping` | 200+ | BBMP ward boundaries |
| `data_freshness` | 15+ | Metadata tracking for each data source |

---

## Pipeline Commands

```bash
# Full seed (migrations + all data)
python -m app.pipelines.seed_all

# Individual seeds
python -m app.pipelines.seed_neighborhoods
python -m app.pipelines.seed_zones
python -m app.pipelines.seed_prices
python -m app.pipelines.seed_transit
python -m app.pipelines.seed_points
python -m app.pipelines.seed_infra

# External data fetchers
python -m app.pipelines.fetch_flood_risk
python -m app.pipelines.fetch_noise_zones
python -m app.pipelines.fetch_delivery_coverage
python -m app.pipelines.fetch_commute_times

# Property intelligence pipelines
python -m app.pipelines.seed_areas
python -m app.pipelines.seed_landmarks
python -m app.pipelines.seed_infrastructure
python -m app.pipelines.scrape_krera              # RERA builder data
python -m app.pipelines.fetch_compdata             # Company data (CIN, NCLT, directors)
python -m app.pipelines.fetch_reviews              # Google reviews sentiment
python -m app.pipelines.compute_trust_scores       # Multi-factor builder trust rating
python -m app.pipelines.enrich_builders_offline     # Builder enrichment

# Score precomputation (requires running server)
python -m app.pipelines.precompute_scores

# AI verification (requires Anthropic API key)
python -m app.pipelines.verify_ai
python -m app.pipelines.verify_ai "Koramangala"  # single neighborhood
```

---

## Running Locally

```bash
# Install everything
make install-dev

# Backend (terminal 1)
make dev-backend    # uvicorn on :8000

# Frontend (terminal 2)
make dev-frontend   # vite on :5173 (proxies /api to :8000)

# Quality checks
make check          # lint + typecheck + test
make format         # auto-format backend
```

---

## Environment Variables

```env
# Required — Backend (.env)
DATABASE_URL=postgresql://...
DB_HOST=...
DB_PORT=6543
DB_NAME=postgres
DB_USER=...
DB_PASSWORD=...

# Optional — Backend
GOOGLE_MAPS_API_KEY=...     # Maps, Distance Matrix, Directions
ANTHROPIC_API_KEY=...        # Claude AI chat, reports, verification, recommendations
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Required — Frontend (.env)
VITE_SUPABASE_URL=...       # Supabase project URL
VITE_SUPABASE_ANON_KEY=...  # Supabase anonymous key (public, safe to expose)
```

---

## Frontend Modes

| Mode | Tab | Feature |
|------|-----|---------|
| Explore | Compass | Map + sidebar — click pins or search neighborhoods for full 17-dimension scores |
| Compare | MapPin | AI-powered recommender — 4 lifestyle questions → top 3 neighborhoods with 3-way radar chart |
| Verify | Shield | Claim checker — paste property ad text, get claims truth-checked against real data |
| Sources | Database | Data sources, scoring methodology, freshness metadata |

### Authentication
- **Login page** with city selection (Bengaluru enabled, Mumbai/Delhi coming soon)
- Email/password signup + Google OAuth via Supabase Auth
- Session persistence across refreshes

### Property Intelligence (integrated into Explore sidebar)
- **Claims tab** — verify ad claims with data-backed verdicts
- **Builders tab** — builder cards with trust scores, RERA data, risk flags
- **Area Intel tab** — infrastructure timelines, pricing, nearby builders
- **AI Brief tab** — Claude-generated buyer advisory (verdict, strengths, risks, price assessment)

---

## Full Database Schema

### neighborhoods (130 rows)
Core table — every neighborhood with PostGIS center point.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| name | text | NO | Unique neighborhood name |
| aliases | text[] | YES | Alternative names |
| center_geog | geography | NO | PostGIS center point |
| radius_km | real | NO | Coverage radius |
| created_at | timestamptz | YES | Auto-set |

### safety_zones (126 rows)
Crime, police, CCTV, streetlight metrics per neighborhood.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| zone_name | text | NO | Area name |
| crime_rate_per_100k | real | YES | Crime incidents per 100K population |
| streetlight_pct | real | YES | Streetlight coverage percentage |
| cctv_density_per_sqkm | real | YES | CCTV cameras per sq km |
| police_density_per_sqkm | real | YES | Police presence per sq km |
| score | real | YES | Computed safety score (0-100) |
| center_geog | geography | YES | Zone center |
| radius_km | real | YES | Zone radius |

### property_prices (126 rows)
Real estate pricing, rent, affordability per neighborhood.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| area | text | NO | Area name |
| avg_price_sqft | integer | YES | Average price per sq ft (INR) |
| price_range_low | integer | YES | Min price per sq ft |
| price_range_high | integer | YES | Max price per sq ft |
| avg_2bhk_lakh | integer | YES | Average 2BHK price (lakhs) |
| avg_3bhk_lakh | integer | YES | Average 3BHK price (lakhs) |
| avg_2bhk_rent | integer | YES | Average 2BHK monthly rent |
| avg_3bhk_rent | integer | YES | Average 3BHK monthly rent |
| avg_maintenance_monthly | integer | YES | Average maintenance charge |
| yoy_growth_pct | real | YES | Year-over-year price growth % |
| rental_yield_pct | real | YES | Annual rental yield % |
| emi_to_income_pct | real | YES | EMI as % of median tech income |
| affordability_score | real | YES | Affordability score (0-100) |
| affordability_label | text | YES | Label (Affordable/Moderate/Expensive/Very Expensive) |
| resale_avg_days_on_market | integer | YES | Average days to sell |
| center_geog | geography | YES | Area center |
| radius_km | real | YES | Area radius |

### pois (25,265 rows)
Points of interest — hospitals, schools, restaurants, etc. from Google Places + curated data.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| place_id | text | YES | Google Places ID |
| name | text | NO | Place name |
| category | text | NO | hospital, school, restaurant, etc. |
| geog | geography | NO | Location |
| rating | real | YES | Google rating |
| user_ratings_total | integer | YES | Number of reviews |
| tags | jsonb | YES | Structured metadata (accreditation, beds, board, rank, fees, etc.) |

### commute_times (5,200 rows)
Driving times from neighborhoods to tech parks (4 modes x 10 parks x 130 neighborhoods).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| tech_park_id | integer | YES | FK → tech_parks |
| mode | text | NO | car_peak, car_offpeak, car_no_traffic, bike |
| duration_min | real | YES | Travel time in minutes |
| distance_km | real | YES | Route distance |
| route_summary | text | YES | Description |

### slum_zones (11,292 rows)
Slum polygons from satellite imagery for cleanliness scoring.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| fid | integer | YES | Feature ID from source |
| deprivation_dn | integer | YES | Deprivation index (0-245, higher = worse) |
| geog | geography | NO | Polygon boundary |
| centroid_geog | geography | YES | Polygon center |

### metro_stations (109 rows)
Namma Metro stations (operational + under construction + planned).

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| name | text | NO | Station name |
| line | text | NO | Purple, Green, Yellow, Pink |
| geog | geography | NO | Location |
| status | text | YES | operational, under_construction, planned |

### waste_infrastructure (358 rows)
BBMP waste facilities for cleanliness scoring.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| name | text | NO | Facility name |
| type | text | NO | dry_waste_centre, landfill, waste_processing, biomethanisation |
| geog | geography | NO | Location |

### flood_risk (130 rows)
Flood risk assessment per neighborhood.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| risk_level | text | YES | low, moderate, high, critical |
| flood_history_events | integer | YES | Historical flood event count |
| elevation_m | real | YES | Elevation above sea level |
| drainage_quality | text | YES | good, moderate, poor, critical |
| waterlogging_prone_spots | text[] | YES | Known waterlogging locations |
| bbmp_flood_ward | boolean | YES | BBMP-designated flood ward |
| score | real | YES | Flood risk score (0-100, higher = safer) |

### noise_zones (130 rows)
Noise exposure estimates per neighborhood.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| airport_flight_path | boolean | YES | Under KIA/HAL flight path |
| highway_proximity_km | real | YES | Distance to nearest highway |
| construction_zones_active | integer | YES | Active metro/road construction nearby |
| avg_noise_db_estimate | real | YES | Estimated ambient noise (dB) |
| noise_label | text | YES | Quiet, Moderate, Noisy, Very Noisy |
| score | real | YES | Noise score (0-100, higher = quieter) |

### delivery_coverage (130 rows)
Quick-commerce service availability per neighborhood.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods |
| swiggy_serviceable | boolean | YES | Swiggy Instamart available |
| zepto_serviceable | boolean | YES | Zepto available |
| blinkit_serviceable | boolean | YES | Blinkit available |
| bigbasket_serviceable | boolean | YES | BigBasket available |
| avg_delivery_min | real | YES | Average delivery time (minutes) |
| coverage_score | real | YES | Coverage score (0-100) |

### neighborhood_verification (130 rows when complete)
Claude AI verification results — verdict, pros/cons, lifestyle tags.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | integer | NO | Primary key |
| neighborhood_id | integer | YES | FK → neighborhoods (unique) |
| confidence | integer | YES | AI confidence (0-100) |
| flags | jsonb | YES | Watch-out items |
| narrative | text | YES | JSON with verdict, pros, cons, best_for, avoid_if, lifestyle_tags |
| verified_at | timestamptz | YES | When verified |
| model_used | text | YES | Claude model version |

### Property Intelligence tables

| Table | Purpose |
|-------|---------|
| builders | Builder profiles with trust score, NCLT, director risk, sentiment, certifications |
| builder_projects | Individual project tracking (RERA number, status, delays) |
| areas | Area metadata and analytics |
| infrastructure_projects | Planned metro/road projects with completion timelines |
| landmark_registry | Unified destination lookup (metro, tech parks, junctions) |
| commute_cache | Point-to-point Google Maps API response cache (with expiry) |

### Other tables

| Table | Rows | Purpose |
|-------|------|---------|
| walkability_zones | 33 | Walkability scores per neighborhood |
| water_zones | 25 | BWSSB water supply stage and hours |
| power_zones | 24 | BESCOM power reliability tier |
| business_opportunity | 32 | Startup density, footfall, commercial rent |
| tech_parks | 10 | Manyata, Embassy, ITPL, Electronic City, etc. |
| bus_stops | 50 | BMTC bus stop locations |
| train_stations | 18 | Railway stations |
| police_stations | 49 | Police station locations |
| hospitals | 31 | Curated hospital seed data |
| schools | 50 | Curated ranked school data |
| aqi_stations | 14 | CPCB air quality monitoring stations |
| aqi_readings | 0 | Hourly AQI readings (optional) |
| future_infra_projects | 7 | Metro/road expansion projects |
| future_infra_stations | 64 | Stations on planned metro lines |
| data_freshness | 18 | Metadata tracking per data source |
| ward_mapping | 0 | BBMP ward boundaries (optional) |
| neighborhood_amenities | 0 | Google Places amenity counts (optional) |

---

## Security

### Threat Model

This application handles user data (auth credentials, location preferences) and calls external APIs with sensitive keys (Google Maps, Anthropic, Supabase). The primary threats are:

1. **Supply chain attacks** — compromised PyPI/npm packages stealing API keys or credentials
2. **Injection attacks** — SQL injection via user-supplied neighborhood names or ad text
3. **Credential exposure** — API keys leaking into git history, logs, or client-side code

### Defenses

| Layer | Defense | Implementation |
|-------|---------|----------------|
| **Dependencies** | Minimal dependency tree, direct SDKs only | Anthropic SDK directly (not LiteLLM), no unnecessary wrappers |
| **Dependency scanning** | `uv audit` (Python) + `npm audit` (Node) | CI workflow (`.github/workflows/security.yml`) + `make security` |
| **SAST** | Bandit static analysis | Catches SQL injection, hardcoded secrets, shell injection, insecure functions |
| **Auto-updates** | GitHub Dependabot | Weekly PRs for Python, npm, and GitHub Actions dependencies |
| **SQL injection** | Parameterized queries everywhere | All DB queries use `$1`/`%s` placeholders, never string interpolation |
| **Secret management** | Environment variables only | `.env` files gitignored, no secrets in code or config files |
| **Auth** | Supabase Auth | Email/password + Google OAuth, session tokens managed by Supabase |
| **CORS** | Explicit origin allowlist | Configured in `main.py` lifespan |
| **API keys** | Server-side only | Google Maps API key served via `/api/config/map`, Anthropic key never exposed to client |

### CI Security Pipeline

```
Push / PR → security.yml
              ├── backend-security
              │     ├── uv audit          (OSV vulnerability database)
              │     └── bandit -r app/    (Python SAST)
              └── frontend-security
                    └── npm audit         (GitHub Advisory Database)
```

### Bandit Configuration

Configured in `pyproject.toml` with skips for false positives:
- **B101** — `assert` in non-test code (used for dev guards)
- **B110** — `try/except/pass` (used in best-effort parsing)
- **B310** — `urllib.urlopen` (controlled URLs only)
- **B405/B314** — XML parsing (no untrusted XML input)
- **B608** — SQL injection (all flagged queries use parameterized placeholders)

### Supply Chain Decision: Anthropic SDK vs LiteLLM

This project uses the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) directly instead of wrapper libraries like LiteLLM. In March 2026, LiteLLM was hit by a [supply chain attack](https://www.bleepingcomputer.com/news/security/popular-litellm-pypi-package-compromised-in-teampcp-supply-chain-attack/) — backdoored versions on PyPI stole credentials, SSH keys, and cloud tokens. LiteLLM sits between your app and every LLM provider's API keys, making it a high-value target.

Using the official SDK directly means fewer dependencies, a smaller attack surface, and no single package that holds all your secrets.

---

## Project Governance

| File | Purpose |
|------|---------|
| `LICENSE` | MIT |
| `README.md` | Setup guide, API overview, data sources |
| `CONTRIBUTING.md` | PR rules, code style, branch protection |
| `CODE_OF_CONDUCT.md` | Contributor Covenant 2.1 |
| `SECURITY.md` | Vulnerability reporting policy |
| `.github/CODEOWNERS` | Auto-assigns reviewer on PRs |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR template (What/Why/How + checklist) |
| `.github/ISSUE_TEMPLATE/` | Bug report + feature request templates |
| `.github/workflows/ci.yml` | Lint + typecheck + test on push/PR |
| `.github/workflows/security.yml` | Dependency audit + SAST on push/PR |
| `.github/dependabot.yml` | Weekly dependency update PRs (Python, npm, Actions) |
| `Makefile` | `install`, `dev`, `check`, `format`, `security`, `build`, `clean` |
