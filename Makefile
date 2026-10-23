# Common developer commands. On Windows use Git Bash, WSL, or `choco install make`;
# every target is a plain command you can also copy into PowerShell.
SIDECAR := services/sidecar
DESKTOP := apps/desktop

.DEFAULT_GOAL := help
.PHONY: help install hooks dev-sidecar dev-web dev-electron seed lint format typecheck test \
        test-sidecar test-desktop coverage migrate migrate-fresh contracts links check build build-sidecar \
        dist-win smoke-sidecar docker-test docker-dev docker-web docker-mlflow docker-down clean

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

install: ## Install Python (uv) and Node dependencies
	cd $(SIDECAR) && uv sync
	npm install

hooks: ## Install the pre-commit and commit-msg git hooks (needs pre-commit on PATH)
	pre-commit install --hook-type pre-commit --hook-type commit-msg

dev-sidecar: ## Run the API on 127.0.0.1:8765 with token "dev" (docs at /docs)
	cd $(SIDECAR) && uv run python -m app --dev

dev-web: ## Run the renderer in a browser against dev-sidecar (http://localhost:5173)
	npm run dev -w $(DESKTOP)

dev-electron: ## Run the full Electron app (spawns its own sidecar)
	npm run dev:electron -w $(DESKTOP)

seed: ## Fill the dev database with 2 weeks of demo data (wipes user data!)
	cd $(SIDECAR) && uv run python -m app.devtools.seed_demo --wipe

migrate: ## Apply Alembic migrations to the configured database
	cd $(SIDECAR) && uv run alembic upgrade head

migrate-fresh: ## Apply every migration to a throwaway database (what CI checks)
	cd $(SIDECAR) && rm -f .migrate-check.db && \
	  ASCEND_DB_URL=sqlite:///.migrate-check.db uv run alembic upgrade head && \
	  ASCEND_DB_URL=sqlite:///.migrate-check.db uv run alembic current && rm -f .migrate-check.db

lint: ## ruff + eslint
	cd $(SIDECAR) && uv run ruff check . && uv run ruff format --check .
	npm run lint

format: ## Auto-format Python
	cd $(SIDECAR) && uv run ruff format . && uv run ruff check --fix .

typecheck: ## mypy + tsc
	cd $(SIDECAR) && uv run mypy app
	npm run typecheck

test: test-sidecar test-desktop ## All tests

test-sidecar: ## pytest
	cd $(SIDECAR) && uv run pytest

test-desktop: ## vitest
	npm test

coverage: ## pytest with an HTML coverage report in services/sidecar/htmlcov/
	cd $(SIDECAR) && uv run pytest --cov=app --cov-report=term-missing --cov-report=html

contracts: ## Compare the sidecar OpenAPI with docs/contracts (drift check)
	cd $(SIDECAR) && uv run --with pyyaml python ../../scripts/check_contract_drift.py

links: ## Check that relative links in the Markdown files resolve
	cd $(SIDECAR) && uv run python ../../scripts/check_md_links.py

check: lint typecheck test migrate-fresh contracts links build ## Everything CI runs, in one go (run before a PR)

build: ## Build renderer + Electron main/preload
	npm run build -w $(DESKTOP)

build-sidecar: ## PyInstaller build -> services/sidecar/dist/ascend-sidecar/
	cd $(SIDECAR) && uv sync --group build && uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm

dist-win: build-sidecar ## Windows installer (run on Windows) -> apps/desktop/release/
	npm run dist:win -w $(DESKTOP)

smoke-sidecar: ## Start the PyInstaller build, check /health, stop it (after build-sidecar)
	cd $(SIDECAR) && uv run python packaging/smoke.py

COMPOSE := docker compose -f docker/docker-compose.yml

docker-test: ## Lint + tests inside the Docker test image
	$(COMPOSE) --profile test run --rm --build sidecar-tests

docker-dev: ## Sidecar API in Docker on http://localhost:8765/docs (read-only, non-root)
	$(COMPOSE) --profile dev up --build sidecar

docker-web: ## Sidecar + renderer (Vite) in Docker; open http://localhost:5173
	$(COMPOSE) --profile web up --build

docker-mlflow: ## MLflow tracking server on http://localhost:5000 (runs + artefacts in a volume)
	$(COMPOSE) --profile ml up mlflow

docker-down: ## Stop every compose service (volumes are kept)
	$(COMPOSE) --profile test --profile dev --profile web --profile ml down

clean: ## Remove build output (keeps your database)
	rm -rf $(DESKTOP)/dist $(DESKTOP)/dist-electron $(DESKTOP)/release $(SIDECAR)/dist $(SIDECAR)/build
