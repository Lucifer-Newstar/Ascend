# Common developer commands. On Windows use Git Bash, WSL, or `choco install make`;
# every target is a plain command you can also copy into PowerShell.
SIDECAR := services/sidecar
DESKTOP := apps/desktop

.DEFAULT_GOAL := help
.PHONY: help install dev-sidecar dev-web dev-electron seed lint format typecheck test \
        test-sidecar test-desktop migrate build build-sidecar dist-win docker-test clean

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

install: ## Install Python (uv) and Node dependencies
	cd $(SIDECAR) && uv sync
	npm install

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

build: ## Build renderer + Electron main/preload
	npm run build -w $(DESKTOP)

build-sidecar: ## PyInstaller build -> services/sidecar/dist/ascend-sidecar/
	cd $(SIDECAR) && uv sync --group build && uv run --group build pyinstaller packaging/ascend-sidecar.spec --noconfirm

dist-win: build-sidecar ## Windows installer (run on Windows) -> apps/desktop/release/
	npm run dist:win -w $(DESKTOP)

docker-test: ## Lint + tests inside the Docker test image
	docker compose -f docker/docker-compose.yml run --rm --build sidecar-tests

clean: ## Remove build output (keeps your database)
	rm -rf $(DESKTOP)/dist $(DESKTOP)/dist-electron $(DESKTOP)/release $(SIDECAR)/dist $(SIDECAR)/build
