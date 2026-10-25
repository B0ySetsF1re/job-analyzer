"""FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import health
from app.db import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    # Startup code goes before `yield`, shutdown code after.
    yield
    await dispose_engine()


app = FastAPI(title="Job Posting Analyzer", version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
