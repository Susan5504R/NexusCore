# Makefile (project root)
# -------------------------------------------------------------------
# High‑level convenience commands for the whole NexusCore repo.
# All paths are relative to the repository root.
# -------------------------------------------------------------------

.PHONY: install      # Install backend + frontend dependencies
.PHONY: test         # Run fast unit tests (skip integration)
.PHONY: test-all     # Run ALL tests, including integration & coverage
.PHONY: lint         # Lint Python and JavaScript/TypeScript
.PHONY: fmt          # Auto‑format code (black, prettier)
.PHONY: coverage     # Run tests with coverage report
.PHONY: docker-up    # Spin up Docker services (chroma, db, etc.)
.PHONY: docker-down  # Tear down Docker services
.PHONY: health       # Quick health‑check against running backend
.PHONY: e2e          # Run frontend end‑to‑end (Playwright) tests

# -------------------------------------------------------------------
# Dependency installation
# -------------------------------------------------------------------
install:
	@echo "Installing backend and frontend dependencies..."
	# Backend (Python)
	@cd backend && python -m venv .venv && . .venv/bin/activate && \
		pip install -r requirements.txt && \
		pip install -r requirements-dev.txt
	# Frontend (Node)
	@cd frontend && npm ci

# -------------------------------------------------------------------
# Testing
# -------------------------------------------------------------------
# Fast unit test suite (no integration marker)

test:
	@echo "Running fast unit tests (skip integration)..."
	@cd backend && . .venv/bin/activate && pytest -m "not integration" -v

# Full test suite – includes integration, coverage and health‑check

test-all:
	@echo "Running full test suite (unit + integration + coverage)..."
	@cd backend && . .venv/bin/activate && pytest -v --cov=app --cov-report=term-missing

# Coverage only (reuse the same command, but print the HTML report)
coverage:
	@cd backend && . .venv/bin/activate && pytest --cov=app --cov-report=html
	@echo "Coverage HTML report generated at backend/htmlcov/index.html"

# -------------------------------------------------------------------
# Linting & formatting
# -------------------------------------------------------------------
lint:
	@echo "Running lint checks (Python, JavaScript/TypeScript)..."
	# Python linters
	@cd backend && . .venv/bin/activate && black --check . && flake8 . && mypy .
	# JS/TS lint (assumes eslint config exists)
	@cd frontend && npx eslint "src/**/*.js" "src/**/*.ts" --max-warnings=0

fmt:
	@echo "Formatting code (black, prettier)..."
	@cd backend && . .venv/bin/activate && black .
	@cd frontend && npx prettier --write "src/**/*.{js,ts,tsx,css,html}" "public/**/*.css"

# -------------------------------------------------------------------
# Docker utilities (compose file lives at the repo root)
# -------------------------------------------------------------------

docker-up:
	@echo "Starting Docker Compose services (including Chroma for integration)..."
	docker compose up -d --build

docker-down:
	@echo "Stopping Docker Compose services..."
	docker compose down

# -------------------------------------------------------------------
# Quick health‑check against the running backend service
# -------------------------------------------------------------------
health:
	@echo "Checking backend health endpoint..."
	@curl -s http://localhost:8000/health | jq .

# -------------------------------------------------------------------
# Frontend end‑to‑end tests (Playwright)
# -------------------------------------------------------------------

e2e:
	@echo "Running Playwright end‑to‑end tests..."
	@cd frontend && npx playwright install && npx playwright test

# -------------------------------------------------------------------
# Convenience target: clean generated artefacts
# -------------------------------------------------------------------
clean:
	@echo "Removing virtualenv, node_modules, coverage reports, etc."
	@rm -rf backend/.venv frontend/node_modules backend/htmlcov .pytest_cache

# End of Makefile
