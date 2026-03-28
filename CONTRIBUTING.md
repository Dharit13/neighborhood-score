# Contributing

Thanks for your interest in contributing! Here's how to get started.

## Setup

1. Fork and clone the repo
2. Install [uv](https://docs.astral.sh/uv/) and copy environment files:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   cp backend/.env.example backend/.env
   # Fill in your own API keys (Google Maps, Anthropic, Supabase)
   ```
3. Install and run:
   ```bash
   make install-dev
   make dev-backend    # terminal 1
   make dev-frontend   # terminal 2
   ```

## Pull Requests

- Keep PRs focused on a single change
- Run `make check` before submitting (lint + typecheck + tests)
- Add a clear description of what changed and why

## Adding a New Scoring Dimension

1. Create a scorer in `backend/app/scorers/`
2. Add the weight to `SCORE_WEIGHTS` in `backend/app/config.py`
3. Wire it into the scoring pipeline in `backend/app/routers/scores.py`
4. Add a frontend card in `frontend/src/components/`

## Reporting Bugs

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Browser/OS if frontend-related

## Code Style

- **Python**: Follow ruff defaults
- **TypeScript**: Follow the existing ESLint config
