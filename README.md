# Bangalore Neighborhood Score Calculator

Data-driven neighborhood scoring for Bangalore home buyers. Computes 6 sub-scores and a composite neighborhood score (0-100) using real, verifiable data sources.

## Scores Computed

| Score | Weight | Data Sources |
|-------|--------|--------------|
| **Walkability** | 20% | OpenStreetMap Overpass API (amenity proximity + pedestrian network density) |
| **Women & Children Safety** | 20% | Karnataka Crime Data 2024, Police Station Locations, BBMP Streetlight Data, Safe City CCTV, NARI Report 2025 |
| **Hospital Access** | 15% | NABH Accredited Hospitals (portal.nabh.co), BBMP Hospital List (data.opencity.in) |
| **School Access** | 15% | Top 50 Ranked Schools (Times Now, IIRF 2024), openbangalore GitHub |
| **Transit Access** | 20% | BMTC Bus Stops (7000+), Namma Metro Stations (83), Indian Railways |
| **Builder Reputation** | 10% | Karnataka RERA Portal, BrickFi Guide, MagicBricks/99acres reviews |

## Quick Start

### Prerequisites

You'll need your own API keys:

| Key | Required | Get it from |
|-----|----------|-------------|
| **Google Maps API Key** | Yes (for maps, geocoding, commute times) | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) — enable Maps JavaScript, Geocoding, Directions, and Places APIs |
| **Anthropic API Key** | Yes (for AI chat, reports, verification) | [Anthropic Console](https://console.anthropic.com/) |
| **Supabase / PostgreSQL** | Yes (data storage) | [Supabase](https://supabase.com/) — create a project with PostGIS enabled |

### Setup

```bash
# 1. Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and configure
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys
```

### Using Make (recommended)
```bash
make install-dev    # Install all dependencies
make dev-backend    # Start backend (in one terminal)
make dev-frontend   # Start frontend (in another terminal)
make check          # Run lint + typecheck + tests
```

### Manual Setup
```bash
# Backend
cd backend
uv sync --group dev
uv run uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Run Tests
```bash
make test
# or manually:
cd backend && uv run pytest tests/ -v
```

## API

### POST /api/scores
```json
{
  "address": "Indiranagar, Bangalore",
  "builder_name": "Sobha"
}
```
Or with coordinates:
```json
{
  "latitude": 12.9716,
  "longitude": 77.6416
}
```

## Data Sources & Attribution

- **OpenStreetMap**: ODbL license — amenities, road networks, transit
- **data.opencity.in**: CC BY 4.0 — crime data, police stations, streetlights, hospitals, schools, metro stations
- **openbangalore GitHub**: Open data — BMTC bus stops, schools, police stations
- **NABH (portal.nabh.co)**: Public accreditation directory
- **Karnataka RERA (rera.karnataka.gov.in)**: Public builder/project complaints
- **Times Now / IIRF**: School rankings 2024
- **NARI Report 2025**: Women's safety city rankings
- **BrickFi / MagicBricks / 99acres**: Builder reputation data
