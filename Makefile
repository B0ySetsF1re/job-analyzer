# Command entry points. Run `make` (or `make help`) to list targets.
# Recipe lines must be indented with a TAB, not spaces.

BACKEND := backend
UV_RUN  := uv run --directory $(BACKEND)

.DEFAULT_GOAL := help
.PHONY: help install dev test lint fmt check db up down

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

install: ## Install runtimes (mise) and Python deps (uv)
	mise install
	uv sync --directory $(BACKEND)

dev: ## Run the API on the host with hot reload (:8000)
	$(UV_RUN) uvicorn app.main:app --reload

test: ## Run backend tests; extra args via ARGS="-k health -x"
	$(UV_RUN) pytest $(ARGS)

lint: ## Lint + format check (no changes)
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .

fmt: ## Auto-fix lint issues and format
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff format .

check: lint test ## Lint + tests (run before committing)

db: ## Start Postgres in Docker (waits until healthy)
	docker compose up -d --wait postgres

up: ## Start Postgres + API container with hot reload
	docker compose --profile api up --build

down: ## Stop all containers (database volume kept)
	docker compose --profile api down
