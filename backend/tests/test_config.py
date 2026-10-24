"""Settings loading. `_env_file=None` keeps your local `.env` out of these tests;
`monkeypatch` sets/removes env vars for one test and restores them afterwards."""

import pytest
from pydantic import ValidationError

from app.config import Settings

DB_URL = "postgresql://user:pass@localhost:5432/db"


def test_reads_values_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    settings = Settings(_env_file=None)

    assert settings.app_env == "prod"
    assert str(settings.database_url) == DB_URL


def test_app_env_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("DATABASE_URL", DB_URL)

    assert Settings(_env_file=None).app_env == "dev"


def test_missing_database_url_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_ENV", "staging"),  # not in the Literal
        ("DATABASE_URL", "mysql://user:pass@localhost/db"),  # wrong scheme
    ],
)
def test_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
