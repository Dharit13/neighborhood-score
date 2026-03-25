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

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
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
