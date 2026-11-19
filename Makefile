# Command entry points. Run `make` (or `make help`) to list targets.
# Recipe lines must be indented with a TAB, not spaces.

BACKEND := backend
UV_RUN  := uv run --directory $(BACKEND)
# Keep in sync with mise.toml
PYTHON  := 3.13

.DEFAULT_GOAL := help
.PHONY: help install dev test lint fmt check db migrate migration create-admin up down

help: ## Show available targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

install: ## Install runtimes (mise, if present), Python deps (uv), create .env if missing
	@if command -v mise >/dev/null 2>&1; then mise install; \
	else echo "mise not found: uv will provide Python $(PYTHON)"; fi
	uv sync --directory $(BACKEND) --python $(PYTHON)
	@test -f .env || (cp .env.example .env && echo "Created .env from .env.example")

dev: ## Run the API on the host with hot reload (:8000)
	$(UV_RUN) uvicorn app.main:app --reload

test: db ## Run backend tests (starts Postgres first); extra args via ARGS="-k health -x"
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

migrate: db ## Apply all pending migrations (starts Postgres first)
	$(UV_RUN) alembic upgrade head

migration: db ## Autogenerate a migration from model changes: make migration MSG="add postings"
	@test -n "$(MSG)" || (echo 'Usage: make migration MSG="describe the change"' && exit 1)
	$(UV_RUN) alembic revision --autogenerate -m "$(MSG)"

create-admin: db ## Create an admin or promote a user (password prompted): make create-admin EMAIL=you@example.com
	@test -n "$(EMAIL)" || (echo 'Usage: make create-admin EMAIL=you@example.com' && exit 1)
	$(UV_RUN) python -m app.cli create-admin "$(EMAIL)"

up: ## Start Postgres + API container with hot reload
	docker compose --profile api up --build

down: ## Stop all containers (database volume kept)
	docker compose --profile api down
