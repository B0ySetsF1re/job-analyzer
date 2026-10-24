"""Application settings, loaded from environment variables and the repo-root `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py → parents[2] is the repo root. Resolved from this file, not the
# working directory, so it works from anywhere. A missing file is ignored (e.g. in Docker,
# where compose passes real env vars instead).
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

type AppEnv = Literal["dev", "test", "prod"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",  # .env also holds POSTGRES_* for docker-compose
    )

    app_env: AppEnv = "dev"
    database_url: PostgresDsn  # required: no default, startup fails if missing


@lru_cache
def get_settings() -> Settings:
    """Settings singleton. Inject with `Depends(get_settings)`; override in tests via
    `app.dependency_overrides[get_settings]`."""
    return Settings()  # required fields come from env
