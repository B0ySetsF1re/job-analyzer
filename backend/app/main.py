"""FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, health
from app.db import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """App startup/shutdown hook: code before `yield` runs on startup, after it on shutdown.

    On shutdown it closes the DB connection pool.
    """
    yield
    await dispose_engine()


app = FastAPI(title="Job Posting Analyzer", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
