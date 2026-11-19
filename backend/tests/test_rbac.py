"""Tests for `require_role` in `app/api/deps.py`.

The dependency is called directly, without HTTP: it's a plain async function that takes a
`User`. The HTTP side (401 before 403) is covered by the admin endpoint tests.
"""

import pytest
from fastapi import HTTPException

from app.api.deps import require_role
from app.models.user import User, UserRole

pytestmark = pytest.mark.anyio


def make_user(role: UserRole) -> User:
    """An unsaved `User` with the given role (no DB needed)."""
    return User(email="someone@example.com", password_hash="$argon2id$fake-hash", role=role)


async def test_require_role_returns_user_with_allowed_role() -> None:
    admin = make_user(UserRole.ADMIN)

    assert await require_role(UserRole.ADMIN)(admin) is admin


async def test_require_role_rejects_other_role_with_403() -> None:
    user = make_user(UserRole.USER)

    with pytest.raises(HTTPException) as exc_info:
        await require_role(UserRole.ADMIN)(user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not enough permissions"


async def test_require_role_accepts_any_of_several_roles() -> None:
    check = require_role(UserRole.USER, UserRole.ADMIN)

    for role in UserRole:
        user = make_user(role)
        assert await check(user) is user
