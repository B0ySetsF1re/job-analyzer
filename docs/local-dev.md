# Local Development

## Overview

The local environment is built from three tools:

- **mise** — installs and pins runtime versions (Python, uv; later Node, terraform, kubectl, helm)
- **uv** — manages Python dependencies and the project virtualenv (`backend/.venv`)
- **Docker Compose** — runs Postgres, and optionally the API in a container

Default workflow: **Postgres in Docker, API on the host** via `uv run`. Running the API on the
host keeps debugging simple (breakpoints, no remote attach). The API container exists but is
opt-in.

---

## Toolchain

### mise

Versions are pinned in `mise.toml` at the repo root:

```toml
[tools]
python = "3.13"
uv = "0.13"

[env]
UV_PYTHON_DOWNLOADS = "never"
```

- `mise install` — installs everything pinned in `mise.toml`
- The global config (`~/.config/mise/config.toml`) pins Python 3.11; the project-level
  `mise.toml` overrides it inside this repo only
- `UV_PYTHON_DOWNLOADS = "never"` — uv must use the mise-provided interpreter instead of
  downloading its own, so there is exactly one source of truth for the Python version
- There is no `.python-version` file (`uv init --no-pin-python`) for the same reason;
  `requires-python = ">=3.13"` in `pyproject.toml` is the code-level constraint

### uv

uv plays the role of pnpm for Python. All commands run from `backend/`:

| Command | What it does | pnpm parallel |
|---|---|---|
| `uv sync` | Create/update `.venv` from `uv.lock` (incl. dev group) | `pnpm install` |
| `uv add <pkg>` | Add a runtime dependency | `pnpm add <pkg>` |
| `uv add --dev <pkg>` | Add a dev dependency | `pnpm add -D <pkg>` |
| `uv remove <pkg>` | Remove a dependency | `pnpm remove <pkg>` |
| `uv run <cmd>` | Run a command inside `.venv` (no activation needed) | `pnpm exec <cmd>` |
| `uv run --directory backend <cmd>` | Same, from the repo root | `pnpm --dir backend exec <cmd>` |

`uv run` finds the project by walking up from the current directory looking for
`pyproject.toml`. Only `backend/` has one — see Gotchas.

### Without mise

mise is recommended but optional. Without it, uv provides Python:

- `UV_PYTHON_DOWNLOADS=never` is set only in `mise.toml`'s `[env]`, so without mise uv
  falls back to its default and **downloads Python 3.13** into its own cache if no matching
  interpreter is installed (like `nvm install`, done automatically)
- `make install` skips `mise install` when mise isn't on `PATH` and runs
  `uv sync --python 3.13`; every other target only needs `uv` and `docker`
- After the first sync, `.venv` remembers its interpreter, so later `uv run` calls need no
  `--python` flag

---

## Makefile

The root `Makefile` is the command runner (the `"scripts"` section of `package.json`, but
language-agnostic). Run `make` with no target to list everything:

| Target | Runs |
|---|---|
| `make install` | `mise install` (skipped if mise isn't installed) + `uv sync --python 3.13` + create `.env` from `.env.example` if missing |
| `make dev` | API on the host with `--reload` |
| `make test` | pytest; extra args via `make test ARGS="-k health -x"` |
| `make lint` | `ruff check` + `ruff format --check` |
| `make fmt` | `ruff check --fix` + `ruff format` |
| `make check` | `lint` then `test` (prerequisites, like `"ci": "pnpm lint && pnpm test"`) |
| `make db` | Postgres only, waits until healthy |
| `make up` / `make down` | Postgres + API container / stop everything |

How to read it:
- `target: prereqs ## description` — the `## ` text is what `make help` prints
- Recipe lines run in a shell, one by one, and stop at the first failure
- `.PHONY` lists targets that are commands, not files (see Gotchas)
- `$(VAR)` is a make variable; `UV_RUN := uv run --directory backend` is why every
  target works from the repo root

---

## Local-only Folders

None of these are committed (all covered by `.gitignore`); all are safe to delete.

| Folder | What it is | Recreate with |
|---|---|---|
| `backend/.venv/` | Virtualenv: interpreter link, installed packages, tool executables (`node_modules` parallel) | `uv sync` |
| `__pycache__/` | Compiled bytecode (`.pyc`), written automatically on import | Any import |
| `.ruff_cache/` | Per-file lint results (`.eslintcache` parallel) | `uv run ruff check .` |
| `.pytest_cache/` | Last-failed test info used by `--lf` | `uv run pytest` |

---

## Running the API

```bash
docker compose up -d                       # Postgres (not used by the app yet)
cd backend
uv run uvicorn app.main:app --reload
```

- **uvicorn** is the ASGI web server; FastAPI is only the framework and never opens a port
  itself. `app.main:app` = "import `app/main.py`, serve its `app` object". NestJS parallel:
  `app.listen(3000)`, but as a separate tool
- **`--reload`** restarts the server on `.py` changes (like `nest start --watch` / nodemon)
- Drop `--reload` when running under a debugger — the reloader runs the app in a child
  process, so breakpoints don't hit

URLs: API `http://localhost:8000`, health `/health`, OpenAPI UI `/docs`.

---

## Docker Compose

`docker-compose.yml` at the repo root defines two services:

| Service | Starts by default? | Purpose |
|---|---|---|
| `postgres` | Yes | Postgres 18, `localhost:5432`, `app`/`app`/`job_analyzer` |
| `api` | No (`profiles: ["api"]`) | API in a container with hot reload |

```bash
docker compose up -d                       # Postgres only
docker compose --profile api up --build    # Postgres + API container
docker compose --profile api down          # stop everything (data kept)
docker compose down -v                     # stop and wipe the database volume
```

### `.env`
- One `.env` at the repo root serves both compose and the backend. Compose reads it
  automatically for `${VAR:-default}` interpolation; the backend reads it via
  pydantic-settings (see [backend.md](backend.md#configuration))
- `DATABASE_URL` in `.env` uses host `localhost` (API on the host). The `api` service sets
  its own `DATABASE_URL` with host `postgres` (the service name on the compose network);
  real env vars beat `.env`, so the container value wins

### Postgres
- Credentials default to `app`/`app`/`job_analyzer` and can be overridden via
  `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` in `.env`
- `pg_isready` healthcheck; the `api` service waits for it via
  `depends_on: condition: service_healthy` (the container being *started* is not enough —
  Postgres needs a few seconds before it accepts connections)
- Data lives in the named volume `pgdata`, so it survives `down` (but not `down -v`)

### API container (`backend/Dockerfile.dev`)
- `.dev` because it is for local development only: dev dependencies installed, `--reload`,
  source bind-mounted. The production image (multi-stage, `--no-dev`, non-root) comes in
  Phase 4. Compose references it explicitly via `dockerfile: Dockerfile.dev`
- Based on the official uv image (`ghcr.io/astral-sh/uv:0.13-python3.13-trixie-slim`), so
  uv and Python are preinstalled
- `pyproject.toml` + `uv.lock` are copied and installed **before** the source, so the
  dependency layer stays cached until the lockfile changes (same trick as copying
  `package.json` + lockfile before `pnpm install`)
- `uv sync --frozen` fails if `uv.lock` is out of date (`pnpm install --frozen-lockfile`)
- `backend/.dockerignore` keeps the host `.venv` out of the build context — it contains
  macOS binaries that won't run on Linux

### Hot reload in the container
- **Bind mount** = a host folder mapped live into the container (not a build-time copy).
  `./backend/app` is mounted at `/app/app`, so edits on the host are seen immediately
- uvicorn `--reload` inside the container picks up the change and restarts

---

## Gotchas

### `mise install` fails: "Python installation is missing a `lib` directory"
- **Cause:** older mise (2025.12) picked the *free-threaded* python-build-standalone
  tarball, whose layout mise didn't expect
- **Fix:** `mise self-update` (works since 2026.10.18)

### `uv run pytest` from the repo root: `ModuleNotFoundError: No module named 'fastapi'`
- **Cause:** there is no `pyproject.toml` at the root, so uv finds no project and runs
  whatever `pytest` is first on `PATH` — here Anaconda's (Python 3.11, no FastAPI). The
  traceback shows `anaconda3/lib/python3.11/site-packages/_pytest/...`
- **Fix:** run from `backend/`, or `uv run --directory backend pytest`
- **Note:** Anaconda's `bin` on `PATH` turns a clear "command not found" into a confusing
  import error. `conda config --set auto_activate_base false` avoids that

### Without mise, uv picks Python 3.14 instead of 3.13
- **Cause:** `requires-python = ">=3.13"` allows any newer version, and there is no
  `.python-version` file (mise is the source of truth). uv takes the first matching
  interpreter, e.g. Homebrew's `python3` 3.14
- **Fix:** `uv sync --python 3.13` (what `make install` does); the version is pinned in the
  Makefile's `PYTHON` variable — keep it in sync with `mise.toml`

### Makefile: inline comment adds trailing spaces to a variable
- `PYTHON := 3.13  # comment` makes the value `"3.13  "` — make keeps the whitespace
  before `#`. Put comments on their own line above the variable

### `docker` talks to Podman, not Docker Desktop
- The `default` Docker context points to a Podman VM (`docker info` → Server Version 5.x,
  Operating System fedora). Compose works with it
- If Compose misbehaves: `docker context use desktop-linux`

### Bind-mounting all of `./backend` breaks imports in the container
- **Cause:** the mount would hide the image's `/app/.venv` behind the host's macOS `.venv`
- **Fix:** mount only the source folder (`./backend/app:/app/app`)

### Hot reload doesn't trigger in the container on macOS
- **Cause:** containers run in a Linux VM; file-change events from macOS don't reliably
  cross into it
- **Fix:** `WATCHFILES_FORCE_POLLING=true` on the `api` service (Node parallel:
  `CHOKIDAR_USEPOLLING`)

### Postgres 18 volume path
- Postgres 18+ images store data under `/var/lib/postgresql/<major>/`; mount the parent
  `/var/lib/postgresql`, not `/var/lib/postgresql/data` as older tutorials show

### `$$` in the compose healthcheck
- `pg_isready -U $${POSTGRES_USER}` — `$$` escapes the variable so Compose doesn't
  interpolate it; the container's shell expands it at runtime

### Makefile: `*** missing separator. Stop.`
- **Cause:** a recipe line is indented with spaces; make requires a real TAB
- **Fix:** re-indent with a TAB (editors usually do this for files named `Makefile`, but
  pasted snippets often carry spaces)

### Makefile: `cd` on one recipe line has no effect on the next
- Each recipe line runs in its own shell. Use `uv run --directory backend` (or
  `cd backend && cmd` on one line) instead. `.ONESHELL` would change this, but macOS ships
  GNU Make 3.81, which doesn't support it

### Makefile: a target "is up to date" and does nothing
- **Cause:** make treats targets as files to build. If a file/folder with the target's name
  exists (e.g. `test`) and the target isn't in `.PHONY`, make skips it
- **Fix:** add every command target to `.PHONY`

### Makefile: `$` in shell commands
- Make expands `$` itself; a literal `$` for the shell must be written `$$` (see the `awk`
  call in `help`)

### uv image tags: versioned tags are trixie-based
- `uv:0.13-python3.13-bookworm-slim` does not exist; versioned tags use Debian trixie
  (`uv:0.13-python3.13-trixie-slim`). Unversioned bookworm tags still exist but aren't pinned
