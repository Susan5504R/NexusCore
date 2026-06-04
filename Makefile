# Makefile (project root)
# -------------------------------------------------------------------
# High‑level convenience commands for the whole NexusCore repo.
# All paths are relative to the repository root.
# -------------------------------------------------------------------

# Detect OS for virtual‑env activation path (Windows uses backslashes)
ifeq ($(OS),Windows_NT)
VENV_ACTIVATE=.venv\\Scripts\\activate
else
VENV_ACTIVATE=.venv/bin/activate
endif

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
.PHONY: clean        # Remove generated artefacts

# -------------------------------------------------------------------
# Dependency installation
# -------------------------------------------------------------------
install:
	@echo "Installing backend and frontend dependencies..."
	# Create (or recreate) a virtual environment in the repo root
	@python -m venv .venv
	# Activate the venv and install Python dependencies
	@. $(VENV_ACTIVATE) && pip install -r backend/requirements.txt && pip install -r backend/requirements-dev.txt
	# Install Node dependencies for the frontend
	@cd frontend && npm ci && cd ..

# -------------------------------------------------------------------
# Testing
# -------------------------------------------------------------------
# Fast unit test suite (no integration marker)
test:
	@echo "Running fast unit tests (skip integration)..."
	@cd backend && . $(VENV_ACTIVATE) && pytest -m "not integration" -v

# Full test suite – includes integration, coverage and health‑check
test-all:
	@echo "Running full test suite (unit + integration + coverage)..."
	@cd backend && . $(VENV_ACTIVATE) && pytest -v --cov=app --cov-report=term-missing

# Coverage only (reuse the same command, but generate HTML report)
coverage:
	@cd backend && . $(VENV_ACTIVATE) && pytest --cov=app --cov-report=html
	@echo "Coverage HTML report generated at backend/htmlcov/index.html"

# -------------------------------------------------------------------
# Linting & formatting
# -------------------------------------------------------------------
lint:
	@echo "Running lint checks (Python, JavaScript/TypeScript)..."
	# Python linters
	@cd backend && . $(VENV_ACTIVATE) && black --check . && flake8 . && mypy .
	# JS/TS lint (requires eslint config)
	@cd frontend && npx eslint "src/**/*.js" "src/**/*.ts" --max-warnings=0

fmt:
	@echo "Formatting code (black, prettier)..."
	@cd backend && . $(VENV_ACTIVATE) && black .
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
# Clean generated artefacts
# -------------------------------------------------------------------
clean:
	@echo "Removing virtualenv, node_modules, coverage reports, etc."
	@rm -rf .venv frontend/node_modules backend/htmlcov .pytest_cache

# End of Makefile
