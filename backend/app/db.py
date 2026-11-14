"""Database wiring: SQLAlchemy 2.0 async engine, sessions and the declarative base."""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy import URL, MetaData, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

# Deterministic constraint/index names, so Alembic can find them again when it later
# alters or drops them (Postgres' auto-generated names aren't predictable).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all ORM models. `Base.metadata` is what Alembic diffs against."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def sqlalchemy_url(database_url: str) -> URL:
    """`postgresql://...` → `postgresql+psycopg://...` (SQLAlchemy needs the driver name).

    DATABASE_URL stays plain libpq style, because Procrastinate (Phase 2) passes it
    straight to psycopg, which doesn't understand the `+psycopg` suffix.
    """
    return make_url(database_url).set(drivername="postgresql+psycopg")


@lru_cache
def get_engine() -> AsyncEngine:
    """Process-wide engine (owns the connection pool). Created on first use."""
    return create_async_engine(sqlalchemy_url(str(get_settings().database_url)))


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Factory for `AsyncSession` objects, bound to the process-wide engine.

    `expire_on_commit=False`: objects stay readable after commit (no implicit reload),
    which matters in async code where lazy attribute loads aren't allowed.
    """
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency: one session per request, closed afterwards.

    Usage: `session: Annotated[AsyncSession, Depends(get_session)]`.
    Commit explicitly in the handler; uncommitted changes are rolled back on close.
    """
    async with get_sessionmaker()() as session:
        yield session


async def dispose_engine() -> None:
    """Close pooled connections on shutdown — only if the engine was ever created."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
