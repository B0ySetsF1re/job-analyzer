"""Tests for `app/cli.py`.

The DB logic (`create_or_promote_admin`) is tested directly with `db_session`. The Typer
command itself is only tested for input validation, which fails before any DB access.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typer.testing import CliRunner

from app.cli import cli, create_or_promote_admin
from app.models.user import User, UserRole
from app.security import hash_password, verify_password

NEW_PASSWORD = "new admin password"


@pytest.mark.anyio
async def test_create_or_promote_admin_creates_admin(db_session: AsyncSession) -> None:
    created = await create_or_promote_admin(db_session, "admin@example.com", NEW_PASSWORD)

    user = await db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert created is True
    assert user is not None
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert verify_password(NEW_PASSWORD, user.password_hash)


@pytest.mark.anyio
async def test_create_or_promote_admin_promotes_existing_user(db_session: AsyncSession) -> None:
    user = User(
        email="someone@example.com",
        password_hash=hash_password("old password"),
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    created = await create_or_promote_admin(db_session, "someone@example.com", NEW_PASSWORD)

    await db_session.refresh(user)
    count = await db_session.scalar(select(func.count()).select_from(User))
    assert created is False
    assert count == 1
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert verify_password(NEW_PASSWORD, user.password_hash)


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
