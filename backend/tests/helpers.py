"""Shared helpers for API tests: store rows through `db_session`, build auth headers.

Plain functions, not fixtures: they take arguments (email, overrides), and a test calls
them as often as it needs (≈ factory functions in a Jest `test/utils.ts`).
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.invite import Invite
from app.models.user import User, UserRole
from app.security import create_access_token, hash_invite_code, hash_password

PASSWORD = "correct horse battery"


async def create_invite(session: AsyncSession, email: str, **overrides: object) -> str:
    """Store a pending invite for `email` and return its plain code."""
    code = f"code-{uuid.uuid4().hex}"
    fields: dict[str, object] = {
        "code_hash": hash_invite_code(code),
        "email": email,
        "expires_at": datetime.now(UTC) + timedelta(days=7),
    }
    session.add(Invite(**(fields | overrides)))
    await session.flush()
    return code


async def create_user(session: AsyncSession, email: str, **overrides: object) -> User:
    """Store a user whose password is `PASSWORD`."""
    fields: dict[str, object] = {"email": email, "password_hash": hash_password(PASSWORD)}
    user = User(**(fields | overrides))
    session.add(user)
    await session.flush()
    return user


def bearer(token: str) -> dict[str, str]:
    """`Authorization: Bearer <token>` header."""
    return {"Authorization": f"Bearer {token}"}


def auth_headers(user: User, settings: Settings) -> dict[str, str]:
    """Headers that authenticate requests as `user`."""
    return bearer(create_access_token(user.id, settings))


async def admin_headers(session: AsyncSession, settings: Settings) -> dict[str, str]:
    """Store an admin and return headers that authenticate as them."""
    admin = await create_user(
        session, f"admin-{uuid.uuid4().hex[:8]}@example.com", role=UserRole.ADMIN
    )
    return auth_headers(admin, settings)
