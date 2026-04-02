# Database Setup Guide

> How to set up the Neighbourhood Score database with **any PostgreSQL + PostGIS** instance — no Supabase required.

The schema is 100% standard PostgreSQL. There are no RLS policies, Supabase-specific functions, or vendor lock-in in the migrations.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| PostgreSQL | 14+ | Any distribution (Homebrew, apt, Docker, managed) |
| PostGIS | 3.3+ | Spatial extension for geography columns and GIST indexes |

### Install (macOS)

```bash
brew install postgresql@16 postgis
brew services start postgresql@16
```

### Install (Ubuntu/Debian)

```bash
sudo apt install postgresql-16 postgresql-16-postgis-3
sudo systemctl start postgresql
```

### Install (Docker)

```bash
docker run -d \
  --name neighborhood-db \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  postgis/postgis:16-3.4
```

---

## 1. Create the Database

```bash
createdb neighborhood_score
psql neighborhood_score -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Verify PostGIS is installed:

```bash
psql neighborhood_score -c "SELECT PostGIS_Version();"
```

---

## 2. Configure Environment Variables

Copy the example and edit for your local PostgreSQL:

```bash
cp backend/.env.example backend/.env
```

For a **local PostgreSQL** setup, use these values:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=neighborhood_score
DB_USER=postgres
DB_PASSWORD=postgres
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neighborhood_score
```

For **Supabase**, use the values from your project dashboard:

```env
DB_HOST=db.YOUR_PROJECT.supabase.co
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.YOUR_PROJECT
DB_PASSWORD=your_db_password
DATABASE_URL=postgresql://postgres.YOUR_PROJECT:PASSWORD@db.YOUR_PROJECT.supabase.co:6543/postgres
```

---

## 3. Run Migrations

Run the SQL migration files **in order**:

```bash
cd backend

psql $DATABASE_URL -f supabase/migrations/001_create_tables.sql
psql $DATABASE_URL -f supabase/migrations/002_create_indexes.sql
psql $DATABASE_URL -f supabase/migrations/003_add_cleanliness.sql
psql $DATABASE_URL -f supabase/migrations/004_add_ward_mapping.sql
psql $DATABASE_URL -f supabase/migrations/005_google_places.sql
psql $DATABASE_URL -f supabase/migrations/006_property_intelligence.sql
```

Or use the pipeline runner:

```bash
uv run python -m app.pipelines.runner migrate
```

This creates **33 tables** with GIST spatial indexes on all geography columns.

---

## 4. Seed Data

### Curated data (no API keys needed)

These load from JSON files bundled in the repo:

```bash
uv run python -m app.pipelines.runner seed --all
```

This seeds: neighborhoods, transit (metro/bus/train), hospitals, schools, police stations, AQI stations, zone scores (safety, water, power, walkability), property prices, builders, future infrastructure, landmarks, and area profiles.

### Live data (requires internet, some need API keys)

```bash
# Free — pulls from open data portals
uv run python -m app.pipelines.runner fetch --bus-stops
uv run python -m app.pipelines.runner fetch --police
uv run python -m app.pipelines.runner fetch --flood
uv run python -m app.pipelines.runner fetch --noise
uv run python -m app.pipelines.runner fetch --slums
uv run python -m app.pipelines.runner fetch --waste
uv run python -m app.pipelines.runner fetch --wards

# Requires GOOGLE_MAPS_API_KEY (~$10 in API credits)
uv run python -m app.pipelines.runner fetch --commute

# Checks delivery platform APIs
uv run python -m app.pipelines.runner fetch --delivery

# Scrapes K-RERA portal
uv run python -m app.pipelines.runner fetch --builders
```

### AI verification (requires ANTHROPIC_API_KEY)

```bash
uv run python -m app.pipelines.runner verify --all
```

### Check data freshness

```bash
uv run python -m app.pipelines.runner status
```

---

## 5. Authentication Without Supabase

The backend uses JWT authentication. Without Supabase, you have two options:

### Option A: Disable auth (development / local use)

Set this env var in `backend/.env`:

```env
AUTH_DISABLED=true
```

Then update `backend/app/auth.py` — replace the `require_auth` function:

```python
async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> dict:
    if os.getenv("AUTH_DISABLED") == "true":
        return {"sub": "dev-user", "role": "authenticated"}
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return _decode_token(credentials.credentials)
```

### Option B: Use your own JWT provider

Any JWT provider that issues HS256 or ES256 tokens works. Set the appropriate env var:

- **HS256**: Set `SUPABASE_JWT_SECRET` to your signing secret
- **ES256**: Set `SUPABASE_JWT_JWK` to your public key as JSON

The backend validates the `audience` claim equals `"authenticated"` — configure your JWT provider to include this.

---

## Schema Overview

### Core Tables (33 total)

| Category | Tables | PostGIS |
|----------|--------|---------|
| **Master** | `neighborhoods` | Yes — center point + radius |
| **Transit** | `metro_stations`, `bus_stops`, `train_stations`, `tech_parks` | Yes |
| **Health** | `hospitals`, `aqi_stations`, `aqi_readings` | Yes (except readings) |
| **Education** | `schools` | Yes |
| **Safety** | `police_stations`, `safety_zones` | Yes |
| **Housing** | `property_prices`, `builders`, `builder_projects`, `areas` | Mixed |
| **Commerce** | `pois`, `business_opportunity` | Yes |
| **Infrastructure** | `future_infra_projects`, `future_infra_stations`, `infrastructure_projects`, `landmark_registry`, `commute_cache` | Mixed |
| **Environment** | `flood_risk`, `noise_zones`, `slum_zones`, `waste_infrastructure` | Mixed |
| **Utilities** | `water_zones`, `power_zones`, `walkability_zones` | Yes |
| **Delivery** | `delivery_coverage` | No |
| **Admin** | `ward_mapping`, `commute_times` | Mixed |
| **System** | `neighborhood_verification`, `data_freshness` | No |

### Spatial Queries Used

The backend uses these PostGIS patterns:

- **KNN (nearest neighbor)**: `ORDER BY geog <-> ST_Point(lon, lat)::geography`
- **Radius search**: `ST_DWithin(geog, point, radius_meters)`
- **Distance**: `ST_Distance(geog, point)`
- **IDW interpolation**: Inverse distance weighting for AQI scores

All geography columns have GIST indexes for O(log n) spatial queries.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `CREATE EXTENSION postgis` fails | PostGIS not installed | Install `postgresql-16-postgis-3` or equivalent |
| `relation does not exist` | Migrations not run | Run all 6 migration files in order |
| Scorer returns 0 or None | Table is empty | Run `uv run python -m app.pipelines.runner seed --all` |
| Connection refused | Wrong host/port | Check `DB_HOST` and `DB_PORT` in `.env` |
| `password authentication failed` | Wrong credentials | Check `DB_USER` and `DB_PASSWORD` in `.env` |
| Spatial queries return nothing | Missing GIST indexes | Run `002_create_indexes.sql` |
