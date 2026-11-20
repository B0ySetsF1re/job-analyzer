"""API tests for `/auth`: register with invite, login, current user.

They go through HTTP (`api_client`) and check the database through the same
`db_session`, which is rolled back after each test.
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.invite import Invite
from app.security import create_access_token
from tests.helpers import PASSWORD, bearer, create_invite, create_user

pytestmark = pytest.mark.anyio


# --- POST /auth/register --------------------------------------------------------------------


async def test_register_creates_user_and_redeems_invite(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "user"
    assert "password_hash" not in body

    invite = await db_session.scalar(select(Invite))
    assert invite is not None
    await db_session.refresh(invite)  # the UPDATE ran as plain SQL; reload the row
    assert invite.used_at is not None
    assert str(invite.used_by) == body["id"]


async def test_register_lowercases_email(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/register",
        json={"email": "Alice@Example.COM", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"


async def test_register_rejects_unknown_code(api_client: httpx2.AsyncClient) -> None:
    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": "nope"},
    )

    assert response.status_code == 400


async def test_register_rejects_used_invite(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com", used_at=datetime.now(UTC))

    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 400


async def test_register_rejects_expired_invite(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    yesterday = datetime.now(UTC) - timedelta(days=1)
    code = await create_invite(db_session, "alice@example.com", expires_at=yesterday)

    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 400


async def test_register_rejects_invite_for_other_email(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/register",
        json={"email": "mallory@example.com", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 400


async def test_register_invite_works_only_once(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com")
    payload = {"email": "alice@example.com", "password": PASSWORD, "invite_code": code}

    first = await api_client.post("/auth/register", json=payload)
    second = await api_client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400


async def test_register_rejects_existing_email(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "alice@example.com")
    code = await create_invite(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": code},
    )

    assert response.status_code == 409


async def test_register_rejects_short_password(api_client: httpx2.AsyncClient) -> None:
    """Schema validation (min_length=8): FastAPI answers 422 before the handler runs."""
    response = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "short", "invite_code": "x"},
    )

    assert response.status_code == 422


# --- POST /auth/login -----------------------------------------------------------------------


async def test_login_returns_token_for_valid_credentials(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/login", json={"email": "Alice@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


async def test_login_rejects_wrong_password(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "alice@example.com")

    response = await api_client.post(
        "/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401


async def test_login_rejects_unknown_email(api_client: httpx2.AsyncClient) -> None:
    response = await api_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401


async def test_login_rejects_inactive_user(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    await create_user(db_session, "alice@example.com", is_active=False)

    response = await api_client.post(
        "/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401


# --- GET /auth/me ---------------------------------------------------------------------------


async def test_me_returns_current_user(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, "alice@example.com")

    response = await api_client.get(
        "/auth/me", headers=bearer(create_access_token(user.id, settings))
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == "alice@example.com"


async def test_me_requires_token(api_client: httpx2.AsyncClient) -> None:
    response = await api_client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_garbage_token(api_client: httpx2.AsyncClient) -> None:
    response = await api_client.get("/auth/me", headers=bearer("not-a-jwt"))

    assert response.status_code == 401


async def test_me_rejects_expired_token(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, "alice@example.com")
    expired = settings.model_copy(update={"jwt_expires_minutes": -1})

    response = await api_client.get(
        "/auth/me", headers=bearer(create_access_token(user.id, expired))
    )

    assert response.status_code == 401


async def test_me_rejects_token_of_deleted_user(
    api_client: httpx2.AsyncClient, settings: Settings
) -> None:
    """A valid signature isn't enough: the user must still exist."""
    token = create_access_token(uuid.uuid4(), settings)

    response = await api_client.get("/auth/me", headers=bearer(token))

    assert response.status_code == 401


async def test_me_rejects_inactive_user(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    """A token issued before deactivation stops working right away."""
    user = await create_user(db_session, "alice@example.com", is_active=False)

    response = await api_client.get(
        "/auth/me", headers=bearer(create_access_token(user.id, settings))
    )

    assert response.status_code == 401


# --- Full flow ------------------------------------------------------------------------------


async def test_register_login_me_flow(
    api_client: httpx2.AsyncClient, db_session: AsyncSession
) -> None:
    code = await create_invite(db_session, "alice@example.com")

    registered = await api_client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": PASSWORD, "invite_code": code},
    )
    login = await api_client.post(
        "/auth/login", json={"email": "alice@example.com", "password": PASSWORD}
    )
    me = await api_client.get("/auth/me", headers=bearer(login.json()["access_token"]))

    assert registered.status_code == 201
    assert me.status_code == 200
    assert me.json()["id"] == registered.json()["id"]
