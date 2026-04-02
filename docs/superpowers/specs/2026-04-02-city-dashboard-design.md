# City Dashboard — Weather & News

**Date**: 2026-04-02
**Status**: Approved

## Overview

Add a "City Pulse" section between Explore and Compare in the authenticated app view. Displays live weather and local news for the user's selected city (currently Bengaluru). No new nav tab — purely scrollable content.

## Data Sources

### Weather — Open-Meteo (free, no API key)
- **Geocoding**: `https://geocoding-api.open-meteo.com/v1/search?name={city}`
- **Current + forecast**: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,apparent_temperature&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=5`

### News — RSS Feeds (free, no API key)
- Google News RSS: `https://news.google.com/rss/search?q={city}&hl=en-IN&gl=IN&ceid=IN:en`
- Times of India Bengaluru: `https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms`
- Deccan Herald Bengaluru: `https://www.deccanherald.com/bengaluru/rss`

## Backend

### New router: `backend/app/routers/city_feed.py`

**`GET /api/weather?city=Bengaluru`**
- Geocodes city name to lat/lon via Open-Meteo geocoding API
- Fetches current weather + 5-day forecast from Open-Meteo forecast API
- Returns JSON:
  ```json
  {
    "city": "Bengaluru",
    "current": {
      "temperature": 28.5,
      "apparent_temperature": 30.1,
      "humidity": 65,
      "wind_speed": 12.3,
      "weather_code": 1
    },
    "daily": [
      { "date": "2026-04-02", "weather_code": 1, "temp_max": 32, "temp_min": 21 }
    ]
  }
  ```
- In-memory cache: 15 minutes per city
- Uses `httpx` (already in dependencies) for async HTTP

**`GET /api/news?city=Bengaluru`**
- Parses RSS feeds using `feedparser` library
- Merges results from all sources, deduplicates by title similarity, sorts by date
- Returns top 8 articles:
  ```json
  {
    "city": "Bengaluru",
    "articles": [
      {
        "title": "...",
        "source": "Times of India",
        "published": "2026-04-02T10:30:00Z",
        "link": "https://...",
        "thumbnail": "https://..." 
      }
    ]
  }
  ```
- In-memory cache: 15 minutes per city

**Dependencies**: Add `feedparser` to backend (`uv add feedparser`)

**Auth**: Both endpoints behind existing `require_auth` middleware.

## Frontend

### New component: `frontend/src/components/CityDashboard.tsx`

**Data flow**:
1. Reads `selectedCity` from `useAuth()` context
2. Calls `/api/weather?city={selectedCity}` and `/api/news?city={selectedCity}` on mount
3. Shows skeleton loaders while fetching

**Layout** (responsive):
- Desktop: Weather card (left, ~40%) + News grid (right, ~60%)
- Mobile: Weather card full width, news cards stacked below

**Weather card**:
- Large current temperature + WMO weather code mapped to icon/description
- Row: humidity, wind speed, feels-like
- 5-day forecast strip: day name + icon + high/low

**News grid**:
- 2-column grid (desktop), 1-column (mobile)
- Each card: title (2-line clamp), source badge, relative time ("2h ago"), thumbnail if available
- Cards open original article in new tab

**Styling**: Dark glass-morphism matching existing sections — `bg-white/[0.03] backdrop-blur-sm`, white text, `brand-9` accents. Wrapped in `Perspective3DContainer`.

### Integration in App.tsx

- New `<section id="city-pulse-section" className="min-h-screen relative z-10">` between `explore-section` and `compare-section`
- Section header: "CITY PULSE" with `<ScrambledText>` effect, green subtitle "Live weather & local news"
- Not added to `SECTION_IDS` — no bottom nav tab, purely scrollable

## Non-goals

- No quick stats row (AQI, traffic) — keep it simple
- No new nav tab
- No real-time updates or WebSockets — simple fetch on mount with cache
