# Conventions

## Overview

How we write code in this repo. Rules only, each with a short reason; the explanations
live in the topic docs, linked from here.

- **What tools enforce is not repeated here.** Line length, import order, unused imports,
  modern syntax (`X | None`, `list[int]`) and formatting are checked by ruff
  (`make lint`, config in `backend/pyproject.toml`, see [backend.md](backend.md#ruff))
- **Rules are added when we agree on them**, in the same change as the code that uses
  them. No rules for phases that haven't started
- Organized by scope: **Shared** (whole repo), **Backend**, and later **Frontend**. If the
  file gets too big, each scope becomes its own file in `docs/conventions/`

---

## Shared

### Git
Commit messages follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):
`<type>(<scope>): <description>`

- **Types:** `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`,
  `style`, `revert`
- **Scopes:** `backend`, `frontend`, `infra`, `helm`, `terraform`, `deps`; omit for
  repo-wide changes
- **Description:** imperative, all lowercase (tool names too), no trailing period
- **Keep it general:** describe the capability, not the libraries. Specifics go in the body
  ```
  ✅ feat(backend): add async orm and migrations setup
  ❌ feat(backend): Added SQLAlchemy and Alembic setup.
  ```
- **Body** (optional): what and why, after a blank line. With the CLI:
  `git commit -m "subject" -m "body"` (each `-m` becomes a paragraph)
- **Breaking changes:** `!` after the type/scope and/or a `BREAKING CHANGE:` footer
- **One logical change per commit:** a commit should be reviewable on its own

### API contract
- **OpenAPI is the source of truth.** FastAPI generates it from the route signatures and
  Pydantic models; it's never edited by hand
- **The frontend client is generated** from `/openapi.json`, never hand-written. Changing a
  Pydantic model must surface as a TS type error in the frontend

---

## Backend

### Python
- **Type hints on every function**, parameters and return type, including tests (`-> None`)
  and fixtures. *Why:* the IDE, FastAPI and Pydantic all read them
- **Abstract types from `collections.abc`:** `AsyncGenerator`, `Generator`, `Sequence`,
  `Mapping`, not `typing.AsyncIterator` & co. Generators (`yield`) are annotated as
  `Generator[T]` / `AsyncGenerator[T]`
- **Type aliases with `type`** (PEP 695): `type AppEnv = Literal["dev", "test", "prod"]`
- **Fixed sets of strings are a `StrEnum`** (or `Literal` for small, local cases).
  Member names `UPPER_CASE`, values lowercase: `PENDING = "pending"`. *Why:* members
  compare equal to their strings and serialize to JSON as plain strings
- **Naming:** `snake_case` for functions, variables and modules; `PascalCase` for classes;
  `UPPER_CASE` for module-level constants
- **Singletons via `@lru_cache`** on a zero-argument getter (`get_settings`, `get_engine`),
  not module-level instances. *Why:* created lazily, and tests can call `.cache_clear()`
- **No code after `return`** and no leftover `...` placeholders once a TODO is done
- **`is None` for optional values** (`T | None` used for defaults or branching). `not x`
  only for real bools, guards that reject anything empty, and "empty counts as missing"
  (`if not items:`). *Why:* `not x` is also true for `0`, `""` and `[]`
  ```python
  ✅ if salary_min is None: salary_min = default
  ❌ if not salary_min: salary_min = default   # an explicit 0 gets replaced
  ```
- **Barrel `__init__.py` only in `app/schemas/`:** it re-exports every schema and lists
  them in `__all__`; import as `from app.schemas import UserRead`. Other packages import
  modules directly (`from app.models.user import User`). *Why:* schemas are a leaf package;
  barrels elsewhere invite circular imports and load more than needed

### Docstrings
Google style. The first line is a one-sentence summary (shown in IDE hovers); details
follow after a blank line.

```python
def make_posting(**overrides: object) -> Posting:
    """Build an unsaved `Posting` with valid required fields.

    Args:
        **overrides: Column values that replace or extend the defaults.

    Returns:
        A new, transient `Posting` (not added to any session).
    """
```

- **App code (`app/`):** every module, public function and public class has one. Empty
  `__init__.py` files (package markers) don't
- **Tests:** only when the name doesn't say *why*: a regression guard, a non-obvious setup,
  a deliberate trick (raw SQL, `expunge_all()`). `test_health_returns_ok_and_env` needs none
- **No types in docstrings:** they're in the signature already. `Args:` / `Returns:` /
  `Raises:` only when they add meaning beyond the names
- **Comments explain *why*, not *what*.** A comment that restates the code gets deleted

### API (FastAPI)
- **One router per resource** in `app/api/<resource>.py`, `router = APIRouter(tags=[...])`,
  registered in `app/main.py`
- **Dependencies as `Annotated[T, Depends(provider)]`**, not `param: T = Depends(provider)`.
  *Why:* the type checker sees `T`, and the alias can be reused
- **The return type is the response schema:** `async def handler(...) -> HealthResponse`.
  Return the model instance, not a dict. See [backend.md](backend.md#return-type--response-schema)
- **Handlers are `async def`**, and never call blocking I/O (ruff's `ASYNC` rules catch
  the common cases)
- **Pydantic schemas are separate from ORM models.** API shapes (`PostingCreate`,
  `PostingRead`) are Pydantic in `app/schemas/<resource>.py`; tables are SQLAlchemy in
  `app/models/`. See [backend.md](backend.md#pydantic)
- **Shared dependencies live in `app/api/deps.py`** (`SessionDep`, `SettingsDep`,
  `CurrentUser`, `<Name>ServiceDep`). Every route except the public ones takes
  `user: CurrentUser`
- **Routes are thin:** validate input (Pydantic), call a service, shape the response.
  Queries and business rules live in services. See [backend.md](backend.md#services)
- **Services are classes in `app/services/<resource>.py`**, constructed with their
  dependencies (`session`, `settings`, ...) and free of FastAPI imports, so the CLI, the
  worker and tests build them directly. Routes get them through a provider in `deps.py`.
  Services commit their own unit of work and take parameter objects (`PaginationParams`,
  request schemas), not loose arguments
- **Services raise `DomainError` subclasses** (`app/errors.py`), never `HTTPException`.
  Each subclass sets `status_code` and `detail`; one handler in `app/main.py` turns them
  into responses. `HTTPException` stays only in `deps.py` (401/403 auth checks)
- **List endpoints are paginated:** the route takes `pagination: PaginationDep` and returns
  `Page[ItemRead]` (`items`, `total`, `limit`, `offset`; limit 1–100, default 20). The
  service takes the `PaginationParams` object and returns `(rows, total)`; `total` is a
  separate `count()` query with the same filters
- **Paginated queries order by a unique tie-breaker:** e.g.
  `.order_by(Model.created_at.desc(), Model.id.desc())`. *Why:* rows with equal sort
  values otherwise come back in any order, so a row can show up on two pages or none
- **Auth failures are generic:** one message per endpoint (`400` for any invite problem,
  `401` for any login or token problem), so responses don't reveal which check failed.
  See [auth.md](auth.md#endpoints)
- **CPU-heavy calls go through `await run_in_threadpool(fn, *args)`** (argon2 hashing and
  verifying), so they don't block the event loop
- **Settings only through `get_settings()`**, never `os.environ` directly
- **Secrets are `SecretStr` settings** (`jwt_secret`), so they never show up in logs or
  tracebacks. Read them with `.get_secret_value()` only where they're used

### Database
Details and reasons: [database.md](database.md).

- **SQLAlchemy 2.0 style:** `name: Mapped[T] = mapped_column(...)`. No legacy `Column(...)`
  without `Mapped`
- **Nullability comes from the annotation:** `Mapped[str]` is NOT NULL,
  `Mapped[str | None]` is nullable. Don't pass `nullable=`
  ```python
  ✅ error: Mapped[str | None] = mapped_column(Text)
  ❌ error: Mapped[str] = mapped_column(Text, nullable=True)   # the type lies
  ```
- **Every table uses the mixins:** `UUIDPrimaryKeyMixin` (Postgres-generated UUID) and
  `TimestampMixin` (`created_at` / `updated_at`)
- **Timestamps are `DateTime(timezone=True)`** (`timestamptz`), never naive `timestamp`
- **Defaults live in the database** (`server_default=`), so raw SQL and other services
  get them too
- **Strings are `Text`**, unless the database must enforce a length
- **Status-like columns are VARCHAR + CHECK** via `str_enum(MyEnum, name="...")` from
  `app/models/types.py`, not native Postgres enums.
  See [database.md](database.md#status-varchar--check-not-a-native-enum)
- **LLM output goes into JSONB.** A field gets its own column only when filtering or
  indexing needs it
- **Every model module is imported in `app/models/__init__.py`**, or autogenerate misses it
- **One `commit()` per unit of work**, at the end. Commit first, then trigger side effects
  (enqueue jobs, call the LLM)
- **Migrations are generated, then reviewed** before `make migrate`: autogenerate misses
  renames, CHECK changes and enum values. Full constraint names in `op.*` calls are
  wrapped in `op.f("...")`

### Tests
Setup and fixtures: [backend.md](backend.md#pytest), [database.md](database.md#testing-with-the-database).

- **Names say what's expected:** `test_<subject>_<expected behavior>`, e.g.
  `test_posting_status_rejects_unknown_values`
- **DB tests use the real test database** through `db_session`. No mocked sessions or
  SQLite. *Why:* JSONB, CHECK constraints and server defaults only exist in Postgres
- **Async tests are marked** `@pytest.mark.anyio` (or `pytestmark = pytest.mark.anyio`
  for a whole module)
- **Replace dependencies with `app.dependency_overrides`**, and clear the overrides in the
  fixture teardown
- **Settings in tests are built explicitly** (`Settings(..., _env_file=None)`), so tests
  don't depend on your local `.env`
- **A new behavior starts as a failing test** that specifies it; the task is to make it green
- **Small factory helpers** (`make_posting(**overrides)`) instead of repeating valid fields
  in every test

### Tooling
- **`make check` before every commit:** lint + all tests
- **ruff decides formatting.** Don't hand-format, and don't argue with `make fmt`
- **Dependencies through uv** (`uv add`, `uv add --dev`), never `pip install`; `uv.lock`
  is committed
