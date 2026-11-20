"""FastAPI application entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import admin, auth, health
from app.db import dispose_engine
from app.errors import DomainError


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """App startup/shutdown hook: code before `yield` runs on startup, after it on shutdown.

    On shutdown it closes the DB connection pool.
    """
    yield
    await dispose_engine()


app = FastAPI(title="Job Posting Analyzer", version="0.1.0", lifespan=lifespan)


@app.exception_handler(DomainError)
async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    """Any `DomainError` from a service → its status code + `{"detail": ...}`.

    Same body shape as FastAPI's `HTTPException`, so clients see one error format.
    """
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
