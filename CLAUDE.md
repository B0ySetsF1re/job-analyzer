# Job Posting Analyzer

## Purpose
Learning + portfolio project. Goal: get hands-on with the Python/AI backend stack
(FastAPI, Pydantic, PydanticAI, Postgres, Procrastinate, OpenTelemetry, Kubernetes, Terraform)
coming from a NestJS/TypeScript background. The author is a senior backend engineer
(Node.js/NestJS, event-driven systems, GraphQL Federation, AWS) who is new to Python.

When helping:
- Explain Python/FastAPI concepts via NestJS/TypeScript parallels where useful.
- Prefer idiomatic, modern Python (3.12+, type hints everywhere, async).
- Keep things simple; this is a time-boxed project. Working end-to-end > polished.

### Working mode (learning project)
- The author reviews every change thoroughly and finishes key parts by hand
  (routers, DB logic, agents, tools) to learn the stack. For these, use
  **scaffold + TODO** mode:
  - Write the skeleton: imports, function signatures, types, decorators,
    Pydantic models, dependency wiring, docstrings.
  - Leave the core logic as numbered `# TODO n:` comments with explicit hints:
    which method/API to use, a short code fragment, and the NestJS/TS parallel
    where helpful. Body ends with `...`.
  - Add a failing pytest test that specifies the expected behavior. The task is
    "make the test green".
  - When they are stuck, escalate hints step by step: leading question →
    concrete hint → full solution with explanation. Don't jump to the solution
    unless asked.
  - After they finish, review: correctness, idiomatic Python, edge cases.
- Boilerplate (Dockerfiles, configs, Terraform, Helm, migrations setup) can be
  generated fully.
- Work in small, reviewable steps. One logical change at a time, no large multi-file dumps.
- Briefly explain non-obvious Python idioms and library choices in each change.
- Update the checklists in the Plan section when a step is done.

### Docs
Topic docs live in `docs/`, one file per area (Overview → Structure → topics → Gotchas):
- `docs/local-dev.md` covers mise, uv, local-only folders, running the API, Docker Compose
  and the dev container. Read it before changing the toolchain, `mise.toml`,
  `docker-compose.yml` or `Dockerfile.dev`.
- `docs/backend.md` covers the backend layout, `pyproject.toml`, packages, app wiring,
  ruff and pytest. Read it before changing project structure or tooling config.

Rules:
- When a non-obvious issue comes up, add it to the relevant doc's **Gotchas** section
  (symptom/cause → fix) in the same change.
- Create a new doc only when its phase starts; no placeholder files.

### Git
- **Never commit (or push) unless explicitly asked.** The author commits by default;
  when a step is done, stop and suggest a commit message instead.
- All commit messages follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):
  `<type>(<scope>): <description>`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `style`, `revert`.
  - Scopes: `backend`, `frontend`, `infra`, `helm`, `terraform`, `deps`, or omit for repo-wide changes.
  - Description: imperative, lowercase, no trailing period (`add health endpoint`, not `Added ...`).
  - Breaking changes: `!` after type/scope and/or a `BREAKING CHANGE:` footer.
  - Optional body (what/why) after a blank line; footers last.

### Toolchain (mise + uv)
- **mise** manages runtime versions (Python 3.13, Node.js, uv, later terraform/kubectl/helm)
  via `mise.toml` at the repo root. Don't install runtimes via Homebrew/pyenv/nvm.
  The global mise config pins Python 3.11 — the project-level `mise.toml` overrides it.
- **uv** manages Python dependencies and the `.venv` (`uv add`, `uv sync`, `uv run`).
  uv must use the mise-provided interpreter, not download its own.
- Docker: the `default` context is Podman; `docker context use desktop-linux` switches
  to Docker Desktop if Compose misbehaves.

### Debugging setup
- Run the API locally via `uv run` with an IDE launch config (no `--reload` while
  debugging, it breaks breakpoints); keep only Postgres in Docker by default.
- Worker runs as a separate process with its own debug config.
- Agent logic should be testable under pytest with PydanticAI `TestModel` / `FunctionModel`,
  so the full flow can be stepped through without real LLM calls.
- If debugging inside Docker is needed: debugpy on port 5678, remote attach.

### Commands
_Fill in as they appear (make dev, make test, make lint, make gen-client, ...)._
Run from `backend/`:
- `uv run pytest` — tests
- `uv run ruff check . && uv run ruff format --check .` — lint
- `uv run uvicorn app.main:app --reload` — API on :8000 (OpenAPI UI at `/docs`)

Run from repo root:
- `docker compose up -d` — Postgres only (default dev setup)
- `docker compose --profile api up --build` — Postgres + API container with hot reload

## What the service does
Turns unstructured job postings (pasted text, later screenshots) into structured, typed data,
stores it in Postgres, and lets the user compare postings against their CV and ask
natural-language questions over the collected postings.

Core idea: the LLM converts messy text into validated Pydantic models; everything after that
is ordinary code and SQL.

## Architecture
- `POST /postings` accepts raw text → stores it with status `pending` → enqueues a Procrastinate job → returns `202`.
- Worker runs a PydanticAI agent with a structured output model (`PostingExtraction`) → saves result, status `processed` / `failed`.
- CV is uploaded once and parsed into a structured `Profile` the same way.
- `match`: fixed-flow LLM call comparing one posting with the profile (structured output, no tools).
- `ask`: tool-using agent that decides which DB queries to run to answer a question.
- Tracing via OpenTelemetry (PydanticAI instrumentation + FastAPI).

### REST API
| Method | Path | Description |
|---|---|---|
| POST | `/postings` | Submit posting text (`{ "source": "...", "text": "..." }`), async processing |
| GET | `/postings` | List with filters (`stack`, `min_salary`, `work_mode`, ...) |
| GET | `/postings/{id}` | Raw text, extracted data, processing status |
| DELETE | `/postings/{id}` | Delete |
| PUT | `/profile` | Upload CV text, parsed into structured profile |
| GET | `/profile` | Get profile |
| POST | `/postings/{id}/match` | Fit analysis: matches, gaps, score |
| POST | `/ask` | Natural-language question over all postings (agent with tools) |
| GET | `/health` | Health check |

OpenAPI is the contract: the frontend TS client is generated from FastAPI's OpenAPI schema.
Changing a Pydantic model must surface as a TS type error in the frontend.

### Extraction model (initial draft)
company, title, seniority, location, work_mode (remote/hybrid/onsite) + office frequency,
relocation_required, salary_min/max/currency, required_skills, nice_to_have_skills,
languages, visa/work-permit requirements, interview_process (list of rounds).

## Stack
**Backend** (`backend/`): Python 3.13 (via mise), uv, FastAPI, Pydantic v2, PydanticAI,
SQLAlchemy 2.0 async (or SQLModel if SQLAlchemy is too heavy), Alembic, Postgres,
Procrastinate (Postgres-based task queue), OpenTelemetry, ruff, pytest.

**Frontend** (`frontend/`): React + Vite + TypeScript, pnpm, generated API client
(openapi-typescript or orval). Optional — only after the backend pipeline works.

**LLM provider**: TBD (Anthropic / OpenAI / Ollama). Keep it configurable via env vars;
PydanticAI is provider-agnostic.

**Infra** (`infra/`): Terraform.
- Backend (api + worker) on EKS via a Helm chart. Postgres in-cluster for the demo
  (or RDS later).
- Frontend: S3 + CloudFront. CloudFront has a second origin (EKS load balancer) with
  behavior `/api/*` → same domain, no CORS.
- ECR for images.
- Static upload in CI: `aws s3 sync` + CloudFront invalidation (not in Terraform).

### Existing reference infrastructure
Repo: `../algorithm-visualizer` — S3 + CloudFront setup written in AWS CDK.
Port the concepts to Terraform (do not mix CDK and Terraform in this project):
- `s3.Bucket` → `aws_s3_bucket` + `aws_s3_bucket_public_access_block`
- `cloudfront.Distribution` → `aws_cloudfront_distribution`
- OAC → `aws_cloudfront_origin_access_control` + bucket policy
- `BucketDeployment` → CI step, not IaC

## Repo layout
```
job-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/        # FastAPI routers
│   │   ├── models/     # Pydantic schemas + DB models
│   │   ├── agents/     # PydanticAI agents and tools
│   │   ├── tasks/      # Procrastinate tasks
│   │   └── main.py
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── docs/               # topic docs (see Docs section)
├── frontend/
├── infra/
│   ├── terraform/
│   └── helm/
├── docker-compose.yml  # postgres, api, worker, (frontend)
├── Makefile            # dev, test, lint, gen-client, ...
└── README.md
```

## Plan
### Phase 0 — Local environment
- [x] Repo, .gitignore, README skeleton, this file
- [x] `backend/` with uv, FastAPI hello world, ruff, pytest
- [x] docker-compose: Postgres + api (hot reload)
- [ ] Makefile entry points
- [ ] Settings via pydantic-settings + `.env.example`

### Phase 1 — Core pipeline
- [ ] DB models + Alembic migrations (postings, profile)
- [ ] `POST/GET/DELETE /postings`
- [ ] PydanticAI extraction agent with `PostingExtraction` output (sync first)
- [ ] `PUT/GET /profile`

### Phase 2 — Async + agents
- [ ] Procrastinate worker; `POST /postings` → 202 + background processing
- [ ] `POST /postings/{id}/match`
- [ ] `POST /ask` agent with DB tools
- [ ] Tests for API and agent tools (mock LLM via PydanticAI TestModel)

### Phase 3 — Observability
- [ ] OpenTelemetry tracing (FastAPI + PydanticAI), local collector/viewer (e.g. Jaeger)

### Phase 4 — Kubernetes
- [ ] Dockerfiles (api, worker), Helm chart
- [ ] Deploy to local cluster (kind or k3d)

### Phase 5 — AWS (stretch)
- [ ] Terraform: VPC, EKS (terraform-aws-modules/eks), ECR, S3 + CloudFront
- [ ] Deploy; tear down with `terraform destroy` after demo (EKS costs money)

### Optional
- [ ] Screenshot input (multipart, vision model)
- [ ] React frontend with generated client
