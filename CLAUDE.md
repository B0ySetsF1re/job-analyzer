# Job Posting Analyzer

## Purpose
Learning + portfolio project. Goal: get hands-on with the Python/AI backend stack
(FastAPI, Pydantic, PydanticAI, Postgres, Procrastinate, OpenTelemetry, Kubernetes, Terraform)
coming from a NestJS/TypeScript background. The author is a senior backend engineer
(Node.js/NestJS, event-driven systems, GraphQL Federation, AWS) who is new to Python.

When helping:
- Explain Python/FastAPI concepts via NestJS/TypeScript parallels where useful.
- Prefer idiomatic, modern Python (3.12+, type hints everywhere, async); follow
  `docs/conventions.md`.
- Keep things simple; this is a time-boxed project. Working end-to-end > polished.

### Working mode (learning project)
- **Ask before changing anything.** Before editing or creating files (code, docs,
  config), show what you plan to change and wait for the author's explicit go-ahead.
  An explicit request for a specific change ("add X to Y") counts as the go-ahead for
  that change only. Reading files, analysis and read-only commands need no confirmation.
- The author reviews every change thoroughly and finishes key parts by hand
  (service methods: business rules and DB queries; agents, tools) to learn the stack.
  Claude writes the rest in full: schemas, models, error classes, thin routes, `deps.py`
  wiring, shared plumbing (pagination, helpers) and mechanical refactors. For the
  author's parts, use **scaffold + TODO** mode:
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
  - When the author says they'll run the tests themselves, only read the code (lint is
    fine); don't run the tests.
- Boilerplate (Dockerfiles, configs, Terraform, Helm, migrations setup) can be
  generated fully.
- Work in small, reviewable steps. One logical change at a time, no large multi-file dumps.
- **The Plan section is binding.** Use the names, endpoints, rules and scope recorded
  there as they are. Any deviation (renaming, refactoring existing code, extra logic such
  as race-safety, a different error hierarchy) goes under `## Decisions` as a question;
  it is never built into the plan.
- **Scaffolds match the complexity of earlier steps.** If a TODO needs a new technique or
  pattern, propose it under `## Decisions` first.
- Briefly explain non-obvious Python idioms and library choices in each change.
- Update the checklists in the Plan section when a step is done.

### Response style
- **Keep replies short.** Give the answer or plan, not the full reasoning; add details
  only when the author asks. Implementation details belong in the TODO hints, not in chat.
- **Open questions go under a `## Decisions` heading**, as a numbered list. Keep
  answered ones in the list as reminders, marked `[Answered]`, without repeating the answer:
  ```
  ## Decisions
  1. [Answered] Schemas folder
  2. `str_enum` helper: yes / no?
  ```
- Refer to topics by name, not by the number of a previous list.
- **When reporting changes, list every file touched**, even in the short format:
  `- <what changed>; <file>, <file>` (files as clickable links).
- **Changes and TODOs are separate sections:** `## Changes` lists what was written and
  the files touched; `## TODOs` lists the author's TODOs (file, numbers, one line each)
  and how to test them. Order: Changes → TODOs → Decisions.
- **Plans before any change use the same layout:** `## Plan` (what Claude will write,
  one line per item, files as clickable links) → `## TODOs` (the author's parts, one line
  each) → `## Decisions`. No reasoning or justification unless the author asks.
- **Decisions are one line each:** `<topic>: <option a> / <option b>`, with the recommended
  option marked `(recommended)`. Explain the trade-offs only when asked.

### Docs
Topic docs live in `docs/`, one file per area (Overview → Structure → topics → Gotchas):
- `docs/local-dev.md` covers mise, uv, local-only folders, running the API, Docker Compose
  and the dev container. Read it before changing the toolchain, `mise.toml`,
  `docker-compose.yml` or `Dockerfile.dev`.
- `docs/backend.md` covers the backend layout, `pyproject.toml`, packages, Pydantic,
  app wiring, ruff and pytest. Read it before changing project structure or tooling config.
- `docs/database.md` covers SQLAlchemy engine/sessions, `get_session`, Alembic config and
  the migration workflow. Read it before touching `app/db.py`, models or `migrations/`.
- `docs/auth.md` covers password hashing, JWT access tokens, invite codes, auth settings
  and (later) `get_current_user` / RBAC. Read it before touching `app/security.py` or auth.
- `docs/conventions.md` holds the coding and commit rules (Shared → Backend). Follow it
  when writing or reviewing code.

Rules:
- When a non-obvious issue comes up, add it to the relevant doc's **Gotchas** section
  (symptom/cause → fix) in the same change.
- When we agree on a new convention, add it to `docs/conventions.md` in the same change.
- Split `docs/conventions.md` by scope once it grows large (rule of thumb: ~300 lines, or
  when the frontend gets its own rules): `docs/conventions/README.md` (shared rules),
  `backend.md`, `frontend.md`, and so on for other scopes. Move sections as they are and
  update every link to them (CLAUDE.md, README, other docs).
- Create a new doc only when its phase starts; no placeholder files.

### Git
- **Never commit (or push) unless explicitly asked.** The author commits by default;
  when a step is done, stop and suggest a commit message instead.
- Commit messages follow the rules in `docs/conventions.md#git` (Conventional Commits,
  all lowercase, general subject, specifics in the body). Suggest them in the
  `git commit -m "subject" -m "body"` form.

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
Prefer the Makefile (repo root; `make` lists all targets):
- `make install` — `mise install` + `uv sync` + create `.env` from `.env.example`
- `make dev` — API on the host with hot reload
- `make test` — pytest (`ARGS="..."` for extra pytest args)
- `make lint` / `make fmt` / `make check` (lint + test)
- `make db` — Postgres only; `make up` / `make down` — full stack with API container
- `make migrate` — apply migrations; `make migration MSG="..."` — autogenerate one
- `make create-admin EMAIL=...` — create (or promote) an admin, password prompted

Underlying commands, run from `backend/`:
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

Multi-user: each user owns their postings and profile; other users' data is invisible.
Registration requires an invite code issued by an admin. Authorization is role-based
(`user`, `admin`).

## Architecture
- `POST /postings` accepts raw text → stores it with status `pending` → enqueues a Procrastinate job → returns `202`.
- Worker runs a PydanticAI agent with a structured output model (`PostingExtraction`) → saves result, status `processed` / `failed`.
- CV is uploaded once and parsed into a structured `Profile` the same way.
- `match`: fixed-flow LLM call comparing one posting with the profile (structured output, no tools).
- `ask`: tool-using agent that decides which DB queries to run to answer a question
  (the current user travels in the agent's deps, so tools only see that user's postings).
- Auth: `POST /auth/login` issues a JWT access token (Bearer header). A `get_current_user`
  dependency guards every route except `/health`, `/auth/register`, `/auth/login`.
  Roles via a `require_role(...)` dependency factory; ownership via `user_id` on every
  query (another user's row → `404`).
- Tracing via OpenTelemetry (PydanticAI instrumentation + FastAPI).

### REST API
| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/auth/register` | public | Create account (`{ email, password, invite_code }`), role `user`; the code is single-use, expires, and is bound to the invited email |
| POST | `/auth/login` | public | Email + password → JWT access token |
| GET | `/auth/me` | user | Current user |
| POST | `/postings` | user | Submit posting text (`{ "source": "...", "text": "..." }`), async processing |
| GET | `/postings` | user | List own postings with filters (`stack`, `min_salary`, `work_mode`, ...) |
| GET | `/postings/{id}` | user | Raw text, extracted data, processing status |
| DELETE | `/postings/{id}` | user | Delete |
| PUT | `/profile` | user | Upload CV text, parsed into structured profile (one per user) |
| GET | `/profile` | user | Get own profile |
| POST | `/postings/{id}/match` | user | Fit analysis: matches, gaps, score |
| POST | `/ask` | user | Natural-language question over own postings (agent with tools) |
| GET | `/admin/users` | admin | List users |
| PATCH | `/admin/users/{id}` | admin | Change role, deactivate |
| DELETE | `/admin/users/{id}` | admin | Delete a user and their data |
| POST | `/admin/invites` | admin | Create an invite for an email; returns the code once |
| GET | `/admin/invites` | admin | List invites (pending / used / expired) |
| DELETE | `/admin/invites/{id}` | admin | Revoke an unused invite |
| GET | `/health` | public | Health check |

OpenAPI is the contract: the frontend TS client is generated from FastAPI's OpenAPI schema.
Changing a Pydantic model must surface as a TS type error in the frontend.

### Extraction model (initial draft)
company, title, seniority, location, work_mode (remote/hybrid/onsite) + office frequency,
relocation_required, salary_min/max/currency, required_skills, nice_to_have_skills,
languages, visa/work-permit requirements, interview_process (list of rounds).

## Stack
**Backend** (`backend/`): Python 3.13 (via mise), uv, FastAPI, Pydantic v2, PydanticAI,
SQLAlchemy 2.0 async, Alembic, Postgres, Procrastinate (Postgres-based task queue),
PyJWT, pwdlib (argon2), OpenTelemetry, ruff, pytest.

**DB decisions** (made at the start of Phase 1):
- SQLAlchemy 2.0 async, not SQLModel: DB models stay separate from API Pydantic schemas.
- psycopg 3 as the only driver (shared with Procrastinate).
- Extracted posting data in a JSONB `extraction` column; promote fields to real columns
  only when filters/indexes need them (e.g. `salary_min`, `work_mode` for `GET /postings`).
- UUID primary keys generated by Postgres (`gen_random_uuid()`).
- User-owned tables have `user_id` → `users.id` (`ON DELETE CASCADE`, indexed);
  `profiles.user_id` is unique (one profile per user). Roles are VARCHAR + CHECK, like statuses.
- Invite codes are stored as SHA-256 hashes, single-use (`used_at` / `used_by`), with
  `expires_at`.

**Frontend** (`frontend/`): React + Vite + TypeScript, pnpm, generated API client
(openapi-typescript or orval). Phase 5, after Kubernetes; kept small (the focus is backend + infra).

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
│   │   ├── api/        # FastAPI routers (thin) + deps.py
│   │   ├── services/   # business logic + queries (classes, no FastAPI)
│   │   ├── models/     # SQLAlchemy models (DB tables)
│   │   ├── schemas/    # Pydantic schemas (API DTOs)
│   │   ├── agents/     # PydanticAI agents and tools
│   │   ├── tasks/      # Procrastinate tasks
│   │   ├── errors.py   # DomainError subclasses → HTTP status via one handler
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
- [x] Makefile entry points
- [x] Settings via pydantic-settings + `.env.example`

### Phase 1 — Core pipeline
- [x] DB models + Alembic migrations (postings, profile)
- [x] Users + authentication: `users` + `invites` tables, invite-code registration,
      JWT login, `GET /auth/me`, `get_current_user`
- [ ] RBAC: `require_role`, `/admin/users`, `/admin/invites`, `make create-admin` (first admin)
  - [x] `require_role` + `AdminUser`
  - [x] `make create-admin` (Typer CLI; promotes, reactivates and resets an existing user)
  - [x] Pagination (`Page[T]`, `PaginationDep`) + admin router + `GET /admin/invites`
  - [x] Service layer refactor (services as classes, `DomainError` + one handler)
  - [ ] `POST /admin/invites`: `{ email, expires_in_days? }` (1–30, default 7), returns the
        plain code once; `409` if the email already has an account; older pending invites
        for the same email are kept. `DELETE /admin/invites/{id}`: `404` unknown, `409`
        already used. Logic in `InviteService` (author's TODOs), new `NotFound` / `Conflict`
  - [ ] `/admin/users`: `GET` (paginated), `PATCH` (role, `is_active`), `DELETE`; an admin
        can't demote, deactivate or delete themselves. Logic in `UserService`
  - [ ] Wrap-up: RBAC section in `docs/auth.md`, check off RBAC
- [ ] `POST/GET/DELETE /postings` (owner-scoped)
- [ ] PydanticAI extraction agent with `PostingExtraction` output (sync first)
- [ ] `PUT/GET /profile` (one per user)

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

### Phase 5 — Frontend (small, time-boxed: ~2–3 sessions)
- [ ] React + Vite app with the TS client generated from OpenAPI (`make gen-client`)
- [ ] Login, postings list + details, profile upload, ask box; no design polish
- [ ] VS Code: TS/TSX formatter (Prettier or Biome) in `.vscode/settings.json` +
      `extensions.json`, like the `[python]` ruff block

### Phase 6 — AWS (stretch)
- [ ] Terraform: VPC, EKS (terraform-aws-modules/eks), ECR, S3 + CloudFront
- [ ] Deploy; tear down with `terraform destroy` after demo (EKS bills ~$0.25–0.30/h
      while up; there is no "stop"). Set an AWS Budgets alert before the first deploy

### Optional
- [ ] Screenshot input (multipart, vision model)
- [ ] Auth extras: httpOnly cookie transport, refresh tokens
