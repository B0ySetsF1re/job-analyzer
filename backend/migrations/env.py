"""Alembic environment: how migrations connect to the DB and what they diff against."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.config import get_settings
from app.db import Base, sqlalchemy_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate compares this metadata (the models) with the live DB schema.
target_metadata = Base.metadata

# Tests pass the test DB URL via Config.attributes; normal CLI runs use app settings.
DATABASE_URL = config.attributes.get("database_url") or sqlalchemy_url(
    str(get_settings().database_url)
)


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`: print the SQL instead of running it."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # NullPool: a one-off CLI run doesn't need a connection pool.
    engine = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        # Alembic's migration API is sync; run_sync bridges it onto the async connection.
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
