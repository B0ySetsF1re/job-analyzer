"""Shared pytest fixtures (auto-discovered by pytest, no import needed)."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    # `with` runs the app's startup/shutdown (lifespan) hooks around each test.
    with TestClient(app) as c:
        yield c
