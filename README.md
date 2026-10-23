# Job Posting Analyzer

Turns unstructured job postings into structured, typed data, stores them in Postgres,
and lets you compare postings against your CV and ask natural-language questions over them.

The LLM converts messy text into validated Pydantic models; everything after that is
ordinary code and SQL.

> Status: early development (Phase 0 — local environment).

## Stack

- **Backend:** Python 3.13, uv, FastAPI, Pydantic v2, PydanticAI, SQLAlchemy 2.0 (async),
  Alembic, Postgres, Procrastinate, OpenTelemetry
- **Frontend (optional):** React + Vite + TypeScript, client generated from OpenAPI
- **Infra:** Docker Compose (local), Helm + Kubernetes, Terraform (AWS: EKS, ECR, S3 + CloudFront)

## Architecture

```
POST /postings ──► Postgres (status: pending) ──► Procrastinate job
                                                       │
                                                       ▼
                                         Worker: PydanticAI extraction agent
                                                       │
                                                       ▼
                                   Postgres (PostingExtraction, status: processed/failed)
```

## Getting started

### Prerequisites

- [mise](https://mise.jdx.dev/): installs the pinned Python / Node / uv versions (`mise install`)
- Docker or Podman (for Postgres)

### Setup

```bash
mise install            # Python 3.13 + uv, as pinned in mise.toml
cd backend
uv sync                 # create .venv and install dependencies (incl. dev group)
```

### Run the API

```bash
cd backend
uv run uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- OpenAPI UI: http://localhost:8000/docs

Drop `--reload` when running under a debugger: the reloader spawns a child process,
so breakpoints won't hit.

### Test and lint

```bash
cd backend
uv run pytest                                      # all tests
uv run pytest tests/test_health.py -v              # one file, verbose
uv run ruff check . && uv run ruff format --check . # lint + format check
uv run ruff format .                               # auto-format
```

_Postgres via docker-compose and Makefile shortcuts will be added later._

## API

_TODO: endpoint table / link to OpenAPI docs (`/docs`)._

## Repo layout

```
backend/    FastAPI app, agents, tasks, migrations, tests
frontend/   React client (optional)
infra/      Terraform + Helm
```
