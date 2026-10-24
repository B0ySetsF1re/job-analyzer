# Backend

## Overview

The backend is a FastAPI application in `backend/`, managed by uv. Python 3.13, type hints
everywhere, async handlers. Tooling: ruff (lint + format) and pytest.

How to install, run and test it: see [local-dev.md](local-dev.md).

---

## Directory Structure

```
backend/
  app/
    __init__.py
    main.py           # FastAPI() instance + router registration
    api/
      __init__.py
      health.py       # GET /health
  tests/
    conftest.py       # shared fixtures (TestClient)
    test_health.py
  pyproject.toml      # project metadata, dependencies, tool config
  uv.lock             # lockfile (committed)
  Dockerfile.dev      # dev container, see local-dev.md
  .dockerignore
```

---

## `pyproject.toml`

The single standard config file for a Python project (PEP 518/621) — the `package.json`
equivalent. `uv.lock` next to it is the lockfile (`pnpm-lock.yaml` equivalent).

| Section | Contains | `package.json` parallel |
|---|---|---|
| `[project]` | Name, version, `requires-python`, runtime `dependencies` | `name`, `version`, `engines`, `dependencies` |
| `[dependency-groups] dev` | pytest, ruff, httpx2 | `devDependencies` |
| `[tool.ruff]`, `[tool.pytest.ini_options]` | Per-tool config | `"jest": {}` / `"eslintConfig": {}` blocks |

There is no `scripts` section in Python packaging; command shortcuts live in the root
`Makefile` (see [local-dev.md](local-dev.md#makefile)).

The project is not packaged (`uv init --bare`, no build system). `app` is importable because
commands run from `backend/` and pytest has `pythonpath = ["."]`.

---

## Packages: `__init__.py`

- An `__init__.py` file marks a directory as a **package**, which is what makes
  `from app.api import health` work
- It runs on first import of the package; ours are empty
- Python 3 can import folders without it ("namespace packages"), but that causes subtle
  issues with pytest and type checkers, so the convention is to always add one
- It *can* re-export names like a TS `index.ts` barrel; we don't do that
- Committed (unlike `__pycache__/`, see [local-dev.md](local-dev.md#local-only-folders))

---

## App Wiring

### `app/main.py`
- Creates the `FastAPI()` instance and registers routers with `app.include_router(...)`
- NestJS parallel: `AppModule` + `NestFactory.create`, but there is no DI container —
  routers are plain module-level objects that get imported

### Routers (`app/api/`)
- `router = APIRouter(tags=[...])` + `@router.get("/path")` — a NestJS `@Controller()`
  with `@Get()` methods
- `tags` group endpoints in the OpenAPI UI (`@ApiTags` parallel)

### Return type = response schema
- `async def health() -> HealthResponse` — FastAPI uses the return annotation to
  **validate** the outgoing data, **serialize** it to JSON and **document** it in OpenAPI.
  No separate `response_model=` or `@ApiResponse` needed
- Response models are Pydantic `BaseModel` subclasses — the DTO-with-class-validator
  equivalent, but validation runs on construction

---

## Tooling

### ruff
Linter **and** formatter in one tool, written in Rust (fast).

| Command | Replaces | JS parallel |
|---|---|---|
| `uv run ruff check .` | flake8, isort, pyupgrade, … | ESLint |
| `uv run ruff format .` | black | Prettier |

Config in `[tool.ruff]`: `line-length = 100`, `target-version = "py313"`. Enabled rule sets
(`[tool.ruff.lint] select`, like ESLint `extends`):

| Code | Rule set | Catches |
|---|---|---|
| `E`, `W` | pycodestyle | Style errors/warnings |
| `F` | pyflakes | Unused imports/variables, undefined names |
| `I` | isort | Import ordering |
| `UP` | pyupgrade | Old syntax (`List[int]` → `list[int]`, `Optional[X]` → `X \| None`) |
| `B` | bugbear | Footguns, e.g. mutable default arguments |
| `SIM` | simplify | Needlessly complex code |
| `ASYNC` | async | Blocking calls inside `async def` |

### pytest
Config in `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["."]`.

**Discovery** (Jest's `*.spec.ts` convention equivalent):
- Files `test_*.py` / `*_test.py` under `tests/`
- Functions `test_*`, or methods `test_*` in classes named `Test*`
- No registration — a new `tests/test_<x>.py` is picked up automatically

**Fixtures** (`tests/conftest.py`) are pytest's DI:
- `conftest.py` is auto-discovered; fixtures defined there are available to all tests
  without imports
- A test requests a fixture by **parameter name**: `def test_x(client: TestClient)`
- `yield` splits setup from teardown — `beforeEach` + `afterEach` in one function
- The `client` fixture wraps `TestClient(app)` in `with`, which runs the app's
  startup/shutdown (lifespan) hooks around each test

**Useful flags** (run from `backend/`):

| Command | Does | Jest parallel |
|---|---|---|
| `uv run pytest -v` | Each test name + result | `--verbose` |
| `uv run pytest tests/test_health.py` | One file | `jest <path>` |
| `uv run pytest tests/test_health.py::test_health_returns_ok` | One test | `-t "<name>"` |
| `uv run pytest -k health` | Filter by name expression | `-t health` |
| `uv run pytest -x` | Stop at first failure | `--bail` |
| `uv run pytest -s` | Show `print()` output | — |
| `uv run pytest --lf` | Rerun last failures | `--onlyFailures` |

The `anyio` pytest plugin (installed with FastAPI) will run `async def` tests later — no
`pytest-asyncio` needed.

---

## Gotchas

### Code after `return` is silently ignored
- Python doesn't flag unreachable code (no TS7027 equivalent), and the enabled ruff rules
  don't either. A leftover `...` or TODO block after `return` just sits there — delete it
- `...` (the `Ellipsis` object) as the only statement is a placeholder like `pass`; after
  other code it's a no-op expression

### `Literal` is enforced at runtime by Pydantic
- `status: Literal["ok"]` — `HealthResponse(status="okay")` raises `ValidationError`.
  Unlike TS literal types, Pydantic checks this when the model is constructed
- Returning a plain dict (`{"status": "ok"}`) also passes (FastAPI validates it against the
  return type), but returning the model instance lets the type checker verify it too

### `StarletteDeprecationWarning`: install `httpx2` instead of `httpx`
- Starlette's `TestClient` deprecated `httpx`; the dev dependency is `httpx2`
