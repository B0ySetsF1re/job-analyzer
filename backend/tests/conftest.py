"""Shared pytest fixtures (auto-discovered by pytest, no import needed)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def get_test_settings() -> Settings:
    """Fixed settings for API tests: independent of your local `.env` and shell env."""
    return Settings(
        app_env="test",
        database_url="postgresql://test:test@localhost:5432/test",
        _env_file=None,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = get_test_settings

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
