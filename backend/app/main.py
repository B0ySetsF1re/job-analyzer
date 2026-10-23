"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.api import health

app = FastAPI(title="Job Posting Analyzer", version="0.1.0")
app.include_router(health.router)
