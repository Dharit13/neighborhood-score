# Neighborhood Score — Architecture

> Data-driven neighborhood scoring platform for Bangalore home buyers. Scores 130+ neighborhoods across 17 livability dimensions using curated data, PostGIS spatial analysis, and Claude AI verification.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Database** | PostgreSQL + PostGIS (Supabase) |
| **DB Drivers** | asyncpg (API), psycopg2 (pipelines) |
| **AI** | Anthropic Claude (verification + chat + reports) |
| **Frontend** | React 19, TypeScript 5.9, Vite 8 |
| **Styling** | Tailwind CSS 4, Framer Motion |
| **Maps** | Google Maps JavaScript API |
| **PDF** | jsPDF (client-side report generation) |
| **Charts** | Recharts |

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
│   │   │   ├── scores.py        # Core scoring API + prefetch + cache
│   │   │   ├── ai_chat.py       # Claude streaming chat
│   │   │   └── report.py        # Claude report generation
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
│   │   │   ├── fetch_*.py       # 12 external data fetchers
│   │   │   ├── precompute_scores.py  # Batch score caching
│   │   │   └── verify_ai.py     # Claude AI verification
│   │   ├── utils/
│   │   │   ├── geo.py           # Geocoding, haversine, walk time
│   │   │   └── overpass.py      # OSM Overpass API client
│   │   └── data/curated/        # 16 curated JSON data files
│   ├── supabase/migrations/     # 5 SQL migration files
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── main.tsx             # React entry
    │   ├── App.tsx              # Main shell: modes, search, prefetch
    │   ├── types.ts             # TypeScript API types
    │   ├── index.css            # Tailwind + theme
    │   ├── data/
    │   │   └── defaultScores.json  # Bundled default for instant load
    │   ├── components/
    │   │   ├── Map.tsx          # Google Map + neighborhood pins
    │   │   ├── MapSidebar.tsx   # Score details sidebar
    │   │   ├── ScoreCard.tsx    # Individual dimension card
    │   │   ├── ScoreRing.tsx    # Animated score ring
    │   │   ├── CompareMode.tsx  # Side-by-side comparison
    │   │   ├── VerifyClaims.tsx # Ad claim verification
    │   │   ├── DataSources.tsx  # Methodology & sources
    │   │   ├── CategoryChips.tsx
    │   │   ├── NeighborhoodInput.tsx
    │   │   ├── ui/             # 15 UI primitives (badge, button, etc.)
    │   │   └── kokonutui/      # Glass card components
    │   ├── utils/
    │   │   ├── generateReport.ts
    │   │   ├── generateComprehensiveReport.ts
    │   │   └── freshnessMap.ts
    │   └── lib/utils.ts        # cn() helper
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

---

## API Endpoints

| Method | Path | Purpose | Response Time |
|--------|------|---------|---------------|
| GET | `/api/prefetch` | All neighborhood pins for map | <100ms (cached) |
| POST | `/api/scores` | Full 17-dimension score | <100ms (cached) / ~13s (live) |
| GET | `/api/neighborhoods` | Neighborhood name list | <200ms |
| GET | `/api/config/map` | Google Maps API key | <50ms |
| GET | `/api/health` | Health check | <50ms |
| GET | `/api/data-freshness` | Data freshness metadata | <200ms |
| POST | `/api/verify-claims` | Verify property ad claims | ~2s |
| POST | `/api/commute/refresh` | Live Google commute data | ~5s |
| POST | `/api/transit/walk` | Live walking directions | ~3s |
| POST | `/api/ai-chat` | Claude streaming chat | SSE stream |
| POST | `/api/generate-report` | Claude PDF report data | ~10s |

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

# Score precomputation (requires running server)
python -m app.pipelines.precompute_scores

# AI verification (requires Anthropic API key)
python -m app.pipelines.verify_ai
python -m app.pipelines.verify_ai "Koramangala"  # single neighborhood
```

---

## Running Locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173 (proxies /api to :8000)
```

---

## Environment Variables

```env
# Required
DATABASE_URL=postgresql://...
DB_HOST=...
DB_PORT=6543
DB_NAME=postgres
DB_USER=...
DB_PASSWORD=...

# Optional
GOOGLE_MAPS_API_KEY=...     # Maps, Distance Matrix, Directions
ANTHROPIC_API_KEY=...        # Claude AI chat, reports, verification
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

## Frontend Modes

| Mode | Tab | Section | Feature |
|------|-----|---------|---------|
| Explore | Compass | Map + Sidebar | Click pins or search neighborhoods |
| Compare | MapPin | Side-by-side | Compare 2 neighborhoods dimension by dimension |
| Verify | Shield | Claim checker | Paste property ad claims, get truth-checked |
| Sources | Database | Methodology | Data sources, scoring methodology |

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

### Other tables

| Table | Rows | Purpose |
|-------|------|---------|
| walkability_zones | 33 | Walkability scores per neighborhood |
| water_zones | 25 | BWSSB water supply stage and hours |
| power_zones | 24 | BESCOM power reliability tier |
| business_opportunity | 32 | Startup density, footfall, commercial rent |
| builders | 25 | RERA projects, complaints, delivery rating |
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
