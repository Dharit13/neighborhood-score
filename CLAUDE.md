# CLAUDE.md — Neighborhood Score

> Project rules for AI assistants working on this codebase.

## Project Overview

Data-driven neighborhood scoring platform for Bangalore home buyers. Scores 130+ neighborhoods across 17 livability dimensions using curated data, PostGIS spatial analysis, and Claude AI verification.

## Architecture

- **Backend**: Python 3.12, FastAPI, asyncpg (PostgreSQL + PostGIS via Supabase)
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS 4
- **AI**: Anthropic Claude SDK (direct — no LiteLLM or wrappers)
- **Database**: Supabase (PostgreSQL + PostGIS)

## Quick Reference

```bash
make install-dev    # Install all dependencies (backend + frontend)
make dev-backend    # Start backend (uvicorn on :8000)
make dev-frontend   # Start frontend (vite on :5173)
make check          # Run ALL checks (lint + typecheck + test + security)
make format         # Auto-format backend code
make test           # Backend tests only
make security       # Dependency audit + SAST
```

## Code Style

### Python (backend/)
- **Formatter/Linter**: ruff (line-length 120, rules: E, F, I, UP)
- **Type checker**: ty (Python 3.12)
- **Async**: Use `async def` for all route handlers and DB calls
- **DB queries**: Always use parameterized queries (`$1`/`%s` placeholders) — never string interpolation
- **Imports**: `load_dotenv()` must run before importing app modules that read env vars

### TypeScript (frontend/)
- **Linter**: ESLint with typescript-eslint
- **Styles**: Tailwind CSS 4 utility classes
- **State**: React hooks, no external state management
- **API calls**: Use fetch with `/api/` prefix (Vite proxies to backend)

## File Structure

```
backend/
  app/
    main.py              # FastAPI app, CORS, rate limiter
    config.py            # Score weights, model config
    db.py                # asyncpg connection pool
    routers/             # API endpoints
    scorers/             # 17 scoring dimension modules
    pipelines/           # Data seeding and precomputation
    utils/               # Shared helpers (geo, overpass, etc.)
  tests/                 # pytest tests
  supabase/migrations/   # SQL migration files (run in order)
frontend/
  src/
    components/          # React components
    pages/               # Route pages
    hooks/               # Custom React hooks
    utils/               # Frontend helpers
```

## Key Conventions

1. **No wrapper libraries for AI** — Use Anthropic SDK directly (supply chain security)
2. **Environment variables for all secrets** — Never hardcode keys, passwords, or URLs
3. **Parameterized SQL everywhere** — No f-strings or `.format()` in queries
4. **Run `make check` before submitting PRs** — Must pass lint, typecheck, tests, and security
5. **Commit messages**: Imperative mood, <72 chars (e.g., "Add flood risk scorer with BBMP ward data")
6. **PRs target `main`**, squash merge preferred

## Security Rules

- Never commit `.env` files or credentials
- Never add LiteLLM or similar API key aggregation libraries
- All new dependencies must pass `uv audit` / `npm audit`
- Use `bandit` to check for Python security issues before merging
- API keys are server-side only — never expose to frontend except via `/api/config/map`

## Testing

- Backend tests in `backend/tests/` using pytest with async support
- Run with `make test` or `cd backend && uv run pytest tests/ -v`
- Mock the database connection pool in tests, not external APIs

## Adding a New Scoring Dimension

1. Create a scorer in `backend/app/scorers/`
2. Add the weight to `SCORE_WEIGHTS` in `backend/app/config.py`
3. Wire it into the scoring pipeline in `backend/app/routers/scores.py`
4. Add a frontend card in `frontend/src/components/`
