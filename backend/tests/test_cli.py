"""Tests for `app/cli.py`: input validation, which fails before any DB access.

The admin logic itself is tested in `test_user_service.py`.
"""

import pytest
from typer.testing import CliRunner

from app.cli import cli

NEW_PASSWORD = "new admin password"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("not-an-email", NEW_PASSWORD),
        ("admin@example.com", "short"),
    ],
)
def test_create_admin_rejects_invalid_input(email: str, password: str) -> None:
    result = CliRunner().invoke(cli, ["create-admin", email, "--password", password])

    assert result.exit_code == 2  # Typer's exit code for a bad parameter
