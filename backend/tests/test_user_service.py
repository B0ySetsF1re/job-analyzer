"""Tests for `UserService`, called directly with `db_session` (no HTTP, no CLI)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.security import hash_password, verify_password
from app.services.users import UserService

pytestmark = pytest.mark.anyio

NEW_PASSWORD = "new admin password"


async def test_create_or_promote_admin_creates_admin(db_session: AsyncSession) -> None:
    created = await UserService(db_session).create_or_promote_admin(
        "admin@example.com", NEW_PASSWORD
    )

    user = await db_session.scalar(select(User).where(User.email == "admin@example.com"))
    assert created is True
    assert user is not None
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert verify_password(NEW_PASSWORD, user.password_hash)


async def test_create_or_promote_admin_promotes_existing_user(db_session: AsyncSession) -> None:
    user = User(
        email="someone@example.com",
        password_hash=hash_password("old password"),
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    created = await UserService(db_session).create_or_promote_admin(
        "someone@example.com", NEW_PASSWORD
    )

    await db_session.refresh(user)
    count = await db_session.scalar(select(func.count()).select_from(User))
    assert created is False
    assert count == 1
    assert user.role == UserRole.ADMIN
    assert user.is_active is True
    assert verify_password(NEW_PASSWORD, user.password_hash)
