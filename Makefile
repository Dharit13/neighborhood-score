.PHONY: install install-dev dev test lint typecheck format check security clean

# ── Setup ─────────────────────────────────────────────────────

install: ## Install all dependencies
	cd backend && uv sync
	cd frontend && npm ci

install-dev: ## Install with dev dependencies
	cd backend && uv sync --group dev
	cd frontend && npm ci

# ── Development ───────────────────────────────────────────────

dev: ## Start backend + frontend (run in separate terminals)
	@echo "Run in separate terminals:"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

dev-backend: ## Start backend dev server
	cd backend && uv run uvicorn app.main:app --reload

dev-frontend: ## Start frontend dev server
	cd frontend && npm run dev

# ── Quality ───────────────────────────────────────────────────

test: ## Run all tests
	cd backend && uv run pytest tests/ -v
	cd frontend && npx vitest run

lint: ## Lint backend + frontend
	cd backend && uv run ruff check .
	cd frontend && npm run lint

typecheck: ## Type check backend + frontend
	cd backend && uv run ty check
	cd frontend && npx tsc -b --noEmit

format: ## Auto-format backend code
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

security: ## Run security scans (dependency audit + SAST)
	cd backend && uv audit || echo "⚠ Dependency vulnerabilities found (review above)"
	cd backend && uv run bandit -r app/ -c pyproject.toml
	cd frontend && npm audit --audit-level=high

check: lint typecheck test security ## Run all checks (lint + typecheck + test + security)

# ── Build ─────────────────────────────────────────────────────

build: ## Build frontend for production
	cd frontend && npm run build

# ── Cleanup ───────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf backend/.ruff_cache backend/.pytest_cache backend/__pycache__
	rm -rf frontend/dist frontend/node_modules/.vite
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ── Help ──────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
