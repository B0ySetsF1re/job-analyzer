"""Health check endpoint."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import AppEnv, Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Response body of `GET /health`."""

    status: Literal["ok"]
    env: AppEnv


@router.get("/health")
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Liveness check. Later (k8s) this can grow a readiness variant that pings the DB."""
    return HealthResponse(status="ok", env=settings.app_env)
