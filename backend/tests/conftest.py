"""Shared pytest fixtures (auto-discovered by pytest, no import needed)."""

from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import httpx2
import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import URL, make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings, get_settings
from app.db import get_session, sqlalchemy_url
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]


def get_test_settings() -> Settings:
    """Fixed settings for API tests: independent of your local `.env` and shell env."""
    return Settings(
        app_env="test",
        database_url="postgresql://test:test@localhost:5432/test",
        jwt_secret="test-secret-that-is-at-least-32-characters",
        _env_file=None,
    )


@pytest.fixture
def settings() -> Settings:
    """The test settings, for code that takes `Settings` as a plain argument."""
    return get_test_settings()


@pytest.fixture
def client() -> Generator[TestClient]:
    """`TestClient` for the app, with test settings injected.

    The `with` block runs the app's lifespan (startup/shutdown). Overrides live on the
    global `app`, so they're cleared afterwards.
    """
    app.dependency_overrides[get_settings] = get_test_settings

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# --- Database -----------------------------------------------------------------------------


@pytest.fixture
def anyio_backend() -> str:
    """Run `@pytest.mark.anyio` tests on asyncio (the anyio plugin would also try trio)."""
    return "asyncio"


@pytest.fixture(scope="session")
def test_database_url() -> URL:
    """Fresh `<db>_test` database with all migrations applied, once per test run.

    Same server and credentials as DATABASE_URL (from `.env`), different database,
    so tests never touch your dev data. Dropped and recreated on every run, which also
    proves the migrations work from an empty database.
    """
    dev_url = make_url(str(get_settings().database_url))
    test_db = f"{dev_url.database}_test"

    # CREATE/DROP DATABASE can't run inside a transaction (hence autocommit), and can't
    # target the database you're connected to (hence the `postgres` maintenance DB).
    admin_dsn = dev_url.set(database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        # sql.Identifier quotes the name safely (DB names can't be bound as parameters).
        conn.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(test_db))
        )
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db)))

    url = sqlalchemy_url(dev_url.set(database=test_db).render_as_string(hide_password=False))

    # Same as `alembic upgrade head`, but in-process and pointed at the test DB
    # (env.py reads `database_url` from attributes). No alembic.ini → no logging setup
    # that would clobber pytest's log capture.
    alembic_cfg = Config(toml_file=BACKEND_DIR / "pyproject.toml")
    alembic_cfg.attributes["database_url"] = url
    command.upgrade(alembic_cfg, "head")

    return url


@pytest.fixture
async def db_session(test_database_url: URL) -> AsyncGenerator[AsyncSession]:
    """An AsyncSession inside a transaction that is rolled back after the test.

    `join_transaction_mode="create_savepoint"`: code under test can call
    `session.commit()` freely; it only releases a SAVEPOINT, and the outer transaction
    is still rolled back at the end. Every test starts with empty tables.
    """
    # NullPool + function scope: one fresh connection per test, no pool shared between
    # the per-test event loops.
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[httpx2.AsyncClient]:
    """Async HTTP client for the app, sharing the test's rolled-back `db_session`.

    Handlers get `db_session` instead of a real session, so whatever they commit is
    rolled back after the test, and the test can read it through the same session.

    Why not `TestClient`: it runs the app on its own event loop, while `db_session`'s
    connection belongs to the test's loop; an async DB connection can't be shared across
    loops. `ASGITransport` calls the app directly on the current loop (no server, no
    network). It doesn't run the lifespan, which these tests don't need.
    """

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = get_test_settings

    transport = httpx2.ASGITransport(app=app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
