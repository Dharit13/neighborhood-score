# Frontend — Neighbourhood Score UI

React 19 + TypeScript + Vite application with dark theme UI.

## Quick Start

```bash
cp .env.example .env     # Configure Supabase credentials
cd .. && make install-dev # Install all dependencies
make dev-frontend         # Start Vite on :5173 (proxies /api to :8000)
```

## Component Architecture

```
App.tsx                    # Main shell — mode tabs, auth gate, layout
├── LoginPage              # Auth (email/password + Google OAuth)
├── SearchAutocomplete     # Global search with category results
├── NeighborhoodMap (Map)  # Google Maps with scored pins
├── MapSidebar             # Score cards, details panel
├── VerifyClaims           # Property ad claim verification
├── CompareMode            # AI-powered neighborhood comparison wizard
└── DataSources            # Data freshness display
```

### Supporting Components

| Component | Purpose |
|-----------|---------|
| `BuilderCard` | Builder profile / summary card |
| `CategoryChips` | Category filter chips |
| `ClaimCard` | Individual claim display for verification |
| `ErrorBoundary` | React error boundary wrapper |
| `InfraTimeline` | Infrastructure timeline view |
| `MetricCard` | Single metric display card |
| `NeighborhoodInput` | Neighborhood name input field |
| `Perspective3DContainer` | 3D perspective wrapper |
| `PropertyIntelligencePanel` | Property intel details panel |
| `RedFlagAlert` | Warning/red flag alert display |
| `ScoreCard` | Score summary card |
| `ScoreRing` | Animated circular score indicator |
| `ScrollReveal3D` | Scroll-triggered 3D reveal effect |
| `Section3DHeading` | 3D-styled section heading |
| `TrustBreakdownChart` | Trust score breakdown chart |
| `TrustScoreCircle` | Circular trust score visual |

### Modes

The app has 4 modes controlled by `AppMode` type:
- `score` — Explore neighborhoods on the map
- `verify` — Paste a property ad, verify claims
- `compare` — Answer questions, get AI recommendations
- `sources` — View data source freshness

## UI Library

| Layer | Technology |
|-------|-----------|
| Base components | shadcn/ui style (`components/ui/`) |
| Animations | Framer Motion |
| Charts | Recharts (radar, bar) |
| Maps | Google Maps JavaScript API |
| 3D effects | Custom hooks (`use3DMouseTrack`) |
| Icons | Lucide React |
| Styling | Tailwind CSS 4 |

### UI Components (`components/ui/`)

`ai-input`, `animated-glowing-search-bar`, `animated-shader-background`, `badge`, `beams-background`, `button`, `card`, `carousel`, `collapsible`, `drawer`, `dropdown-menu`, `input`, `logos3`, `neon-gradient-card`, `shuffle-number`, `sidebar-aurora`, `skeleton`, `tetris-loader`

## State Management

- **No external state library** — React `useState` + props
- **Auth**: `AuthContext` (Supabase session, login/logout/signup)
- **API data**: Fetched in components, passed down as props
- **City selection**: `localStorage` (`ns_selected_city`)

## Key Files

| File | Purpose |
|------|---------|
| `App.tsx` | Main app shell, routing, mode tabs |
| `types.ts` | All TypeScript interfaces |
| `contexts/AuthContext.tsx` | Supabase auth provider |
| `utils/trustTiers.ts` | Trust score → tier mapping |
| `utils/categories.ts` | Category definitions + counting |
| `utils/freshnessMap.ts` | Data freshness calculations |
| `utils/generateReport.ts` | PDF report generation |
| `utils/generateComprehensiveReport.ts` | Full comprehensive PDF report |
| `hooks/use3DMouseTrack.ts` | 3D tilt effect hook |
| `lib/supabase.ts` | Supabase client init |
| `lib/utils.ts` | `cn()` class merging utility |

## Adding a New Mode

1. Add to `AppMode` type in `App.tsx`: `type AppMode = 'score' | 'verify' | 'compare' | 'sources' | 'yourmode';`
2. Add tab config in `MODE_TAB_GRADIENTS` and `SECTION_IDS`
3. Create your component in `components/YourMode.tsx`
4. Add the section in App's return JSX with matching `id={SECTION_IDS.yourmode}`
5. Import and render conditionally

## Development

```bash
npm run dev       # Vite dev server
npm run build     # Production build
npm run lint      # ESLint
npm run test      # Vitest
npm run test:watch # Vitest watch mode
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase anonymous/public key |

### API Proxy

Vite proxies `/api/*` to `http://localhost:8000` in development (configured in `vite.config.ts`).

## Testing

Tests are in `src/__tests__/` using Vitest + React Testing Library.

```bash
npm run test           # Run all tests
npm run test:watch     # Watch mode
```

Test structure:
- `__tests__/utils/` — Pure utility function tests
- `__tests__/components/` — Component render tests
