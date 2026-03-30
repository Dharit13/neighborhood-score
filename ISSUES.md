# Contributor Issues

A curated list of GitHub issues for contributors. Pick one that matches your skill level and interest, then open a PR referencing the issue number.

---

## Good First Issues

### 1. Add Bangalore bounding-box validation to /api/scores

**Labels:** `good-first-issue`, `bug`
**Effort:** S

**Description:**
The `/api/scores` endpoint currently accepts any latitude/longitude pair without checking whether the coordinates fall within Bangalore. Requests for coordinates outside the city return misleading empty or nonsensical scores instead of a clear error.

Add validation that rejects coordinates outside the Bangalore metropolitan bounding box (approximately 12.5--13.5 N, 77.0--78.2 E). Return a `400 Bad Request` with a JSON error body explaining the valid range.

**Files to modify:**
- `backend/app/routers/scores.py` -- add validation before score computation
- `backend/app/config.py` -- define `BANGALORE_BOUNDS` constants

**Acceptance criteria:**
- [ ] Requests with lat/lon inside the bounding box continue to work as before
- [ ] Requests outside the box return HTTP 400 with `{"detail": "Coordinates out of Bangalore bounds"}`
- [ ] Bounds constants live in `config.py`, not hard-coded in the router
- [ ] At least two unit tests: one inside bounds, one outside

---

### 2. Improve .env.example documentation

**Labels:** `good-first-issue`, `documentation`
**Effort:** S

**Description:**
Both `.env.example` files list variable names but lack context. New contributors waste time figuring out which variables are required, what formats are expected, and where to obtain API keys.

Add inline comments to every variable explaining its purpose, whether it is required or optional, and an example value.

**Files to modify:**
- `backend/.env.example`
- `frontend/.env.example`

**Acceptance criteria:**
- [ ] Every variable has a comment on the line above it
- [ ] Required variables are marked `# (required)`; optional ones `# (optional, defaults to ...)`
- [ ] Sensitive values use obviously fake placeholders (e.g., `sk-REPLACE_ME`)
- [ ] No real secrets are committed

---

### 3. Document builder trust score formula

**Labels:** `good-first-issue`, `documentation`
**Effort:** S

**Description:**
`compute_trust_scores.py` calculates a trust score from 7 factors but the formula, weights, and normalisation are not documented. Contributors working on the property intelligence features need to understand the scoring model without reading every line of code.

Add a module-level docstring and per-function docstrings that explain the formula clearly.

**Files to modify:**
- `backend/app/pipelines/compute_trust_scores.py`

**Acceptance criteria:**
- [ ] Module docstring lists all 7 factors with their weights
- [ ] Normalisation method (min-max, z-score, etc.) is explained
- [ ] Edge cases (missing data, zero scores) are documented
- [ ] Docstrings pass `ruff check` and `ty` without new warnings

---

## Testing

### 4. Add backend scorer unit tests

**Labels:** `testing`
**Effort:** M

**Description:**
Each of the 17 neighbourhood scorers (safety, transit, schools, healthcare, green cover, air quality, noise, water quality, walkability, nightlife, grocery access, gym/fitness, pet friendliness, family friendliness, investor ROI, rental yield, appreciation potential) needs dedicated unit tests. Currently test coverage for individual scorers is minimal.

Write tests that feed sample coordinates with mocked database responses and verify that each scorer returns a numeric value in 0--100 and assigns a human-readable label.

**Files to modify:**
- `backend/tests/` -- create or extend test files per scorer

**Acceptance criteria:**
- [ ] At least one test per scorer (17 total minimum)
- [ ] Database calls are mocked (no live Supabase dependency)
- [ ] Each test asserts score is a number in [0, 100]
- [ ] Each test asserts a label string is returned (e.g., "Excellent", "Good", "Average", "Poor")
- [ ] Tests pass in CI with `make test`

---

### 5. Add backend property intelligence route tests

**Labels:** `testing`
**Effort:** M

**Description:**
The property intelligence endpoints (`/api/builders`, `/api/builder/{slug}`, `/api/search`) lack route-level tests. Add tests using `httpx.AsyncClient` with FastAPI's `TestClient` pattern and mocked Supabase responses.

**Files to modify:**
- `backend/tests/` -- create test file for property intelligence routes

**Acceptance criteria:**
- [ ] Test `GET /api/builders` returns a list with expected schema
- [ ] Test `GET /api/builder/{slug}` returns 200 for valid slug, 404 for unknown slug
- [ ] Test `GET /api/search?q=...` returns filtered results
- [ ] All external dependencies are mocked
- [ ] Tests pass in CI with `make test`

---

## Enhancement

### 6. Add global error boundary to frontend

**Labels:** `enhancement`
**Effort:** S

**Description:**
Unhandled React errors currently crash the entire app with a white screen. Add an `ErrorBoundary` component that catches render errors and shows a user-friendly fallback with a retry button.

**Files to modify:**
- `frontend/src/components/ErrorBoundary.tsx` -- new file
- `frontend/src/App.tsx` -- wrap top-level routes with ErrorBoundary

**Acceptance criteria:**
- [ ] `ErrorBoundary` is a class component using `componentDidCatch`
- [ ] Fallback UI shows a friendly message and a "Try Again" button that reloads the page
- [ ] Error details are logged to `console.error`
- [ ] App does not white-screen on a thrown render error
- [ ] Component has at least one unit test (e.g., render a child that throws)

---

### 7. Add pagination to /api/builders endpoint

**Labels:** `enhancement`, `performance`
**Effort:** M

**Description:**
`/api/builders` returns every builder in a single response. As the dataset grows this will become slow and wasteful. Add `limit` and `offset` query parameters and return a `total` count alongside the results so the frontend can paginate.

**Files to modify:**
- `backend/app/routers/property_intelligence.py`

**Acceptance criteria:**
- [ ] `GET /api/builders` accepts optional `limit` (default 20, max 100) and `offset` (default 0) query params
- [ ] Response body includes `{"items": [...], "total": <int>, "limit": <int>, "offset": <int>}`
- [ ] Existing frontend calls continue to work (backwards compatible defaults)
- [ ] At least two tests: default pagination, custom limit/offset
- [ ] Invalid values (negative offset, limit > 100) return 422

---

### 8. Cache neighbourhood summaries for AI chat

**Labels:** `enhancement`, `performance`
**Effort:** M

**Description:**
`_get_neighborhood_summary()` in the AI chat router executes 12 LEFT JOINs against the database on every question. Since neighbourhood data only changes when pipelines run, summaries should be cached in memory at startup, similar to how `_score_cache` already works.

**Files to modify:**
- `backend/app/routers/ai_chat.py`

**Acceptance criteria:**
- [ ] Neighbourhood summaries are loaded into an in-memory cache on app startup
- [ ] `_get_neighborhood_summary()` reads from cache instead of hitting the database
- [ ] Cache is invalidated/refreshed when pipelines run (or on a configurable TTL)
- [ ] Response latency for AI chat questions drops measurably (add a log or metric)
- [ ] Existing behaviour and response format are unchanged

---

### 9. Consistent loading states across frontend

**Labels:** `enhancement`
**Effort:** M

**Description:**
The frontend uses ad-hoc loading indicators (spinners, text, blank states) inconsistently across components. Replace them with a unified skeleton loader pattern for a polished user experience.

**Files to modify:**
- `frontend/src/components/` -- Map, CompareMode, VerifyClaims, and any other components with loading states

**Acceptance criteria:**
- [ ] A reusable `Skeleton` component exists (or a shared utility)
- [ ] Map view shows skeleton placeholders while tiles and pins load
- [ ] CompareMode questionnaire steps show skeletons during data fetch
- [ ] VerifyClaims shows skeletons while claim analysis runs
- [ ] No raw "Loading..." text strings remain in the codebase
- [ ] Skeleton animations are smooth (CSS transitions, no layout shift)

---

### 10. Add data freshness tracking to pipelines

**Labels:** `enhancement`
**Effort:** L

**Description:**
There is no way to tell when pipeline data was last refreshed. Each `fetch_*.py` pipeline should record a timestamp and status in a `data_freshness` table after a successful run. Create a shared helper function that all pipelines call.

**Files to modify:**
- `backend/app/pipelines/` -- update each `fetch_*.py` file
- `backend/app/lib/freshness.py` -- new helper module

**Acceptance criteria:**
- [ ] `data_freshness` table schema is defined (pipeline_name, last_run_at, status, row_count)
- [ ] `backend/app/lib/freshness.py` exports a `record_freshness(pipeline_name, status, row_count)` function
- [ ] Every `fetch_*.py` pipeline calls `record_freshness` on completion
- [ ] A new `GET /api/freshness` endpoint returns the current freshness state for all pipelines
- [ ] At least one test for the helper function

---

## Accessibility

### 11. Add ARIA labels to interactive components

**Labels:** `accessibility`
**Effort:** M

**Description:**
Several interactive elements are missing proper ARIA attributes, making the app difficult to use with screen readers. Map pins, the search autocomplete dropdown, builder card expansion toggles, and the CompareMode questionnaire need attention.

**Files to modify:**
- `frontend/src/components/` -- Map, SearchAutocomplete, BuilderCard, CompareMode

**Acceptance criteria:**
- [ ] Map pins have `aria-label` describing the location name and score
- [ ] SearchAutocomplete uses `role="combobox"`, `aria-expanded`, `aria-activedescendant`
- [ ] BuilderCard expansion toggle has `aria-expanded` and `aria-controls`
- [ ] CompareMode questionnaire steps use `role="radiogroup"` or appropriate roles
- [ ] No new accessibility warnings from `eslint-plugin-jsx-a11y`
- [ ] Manual screen reader test confirms navigability (document in PR description)

---

### 12. Mobile responsive improvements

**Labels:** `accessibility`, `enhancement`
**Effort:** L

**Description:**
The app is primarily designed for desktop viewports. On mobile, the MapSidebar overlaps the map, the radar chart in CompareMode is too small to read, and several tap targets are under 44px.

**Files to modify:**
- `frontend/src/components/` -- MapSidebar, CompareMode, and related components

**Acceptance criteria:**
- [ ] MapSidebar becomes a bottom sheet (draggable drawer) on viewports under 768px
- [ ] Radar chart in CompareMode scales or switches to a list view on small screens
- [ ] All interactive elements meet the 44x44px minimum tap target size
- [ ] No horizontal scroll on any page at 320px width
- [ ] Tested on Chrome DevTools mobile emulator (iPhone SE, Pixel 5)

---

## Documentation

### 13. Add backend README

**Labels:** `documentation`
**Effort:** M

**Description:**
The `backend/` directory has no README. New contributors need a guide that explains the project structure, how to set up the environment, how to troubleshoot common issues, and an overview of the database schema.

**Files to modify:**
- `backend/README.md` -- new file

**Acceptance criteria:**
- [ ] Covers directory structure with one-line descriptions of each module
- [ ] Step-by-step environment setup (uv install, .env config, database migration)
- [ ] Troubleshooting section with at least 3 common issues and solutions
- [ ] Database schema overview (tables, key relationships)
- [ ] Instructions for running individual pipelines

---

### 14. Add frontend README

**Labels:** `documentation`
**Effort:** M

**Description:**
The `frontend/` directory has no README. Contributors need to understand the component architecture, how to add a new mode or tab, and the state management approach.

**Files to modify:**
- `frontend/README.md` -- new file

**Acceptance criteria:**
- [ ] Component tree overview (App -> modes -> components)
- [ ] How to add a new mode/tab (step-by-step)
- [ ] State management patterns used (React context, hooks, etc.)
- [ ] Development server setup and environment variables
- [ ] How to run linting and tests locally

---

### 15. Expand CONTRIBUTING.md

**Labels:** `documentation`
**Effort:** M

**Description:**
The existing `CONTRIBUTING.md` covers basic PR workflow but lacks practical details about running pipelines locally, testing against a local Supabase instance, and debugging common issues.

**Files to modify:**
- `CONTRIBUTING.md`

**Acceptance criteria:**
- [ ] Section on running individual pipelines with example commands
- [ ] Section on setting up and testing against local Supabase (Docker)
- [ ] Debugging guide with at least 5 common scenarios and solutions
- [ ] Updated prerequisites list (uv, Node.js version, Docker)
- [ ] Section on how to add a new scorer to the backend
