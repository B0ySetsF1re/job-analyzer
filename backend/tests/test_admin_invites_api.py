"""API tests for `/admin/invites`: list (access, status, order, pagination), create, revoke."""

import uuid
from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.invite import Invite
from app.models.user import UserRole
from tests.helpers import PASSWORD, admin_headers, auth_headers, create_invite, create_user

pytestmark = pytest.mark.anyio

NOW = datetime.now(UTC)


async def test_list_invites_requires_token(api_client: httpx2.AsyncClient) -> None:
    response = await api_client.get("/admin/invites")

    assert response.status_code == 401


async def test_list_invites_forbids_non_admin(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, "user@example.com", role=UserRole.USER)

    response = await api_client.get("/admin/invites", headers=auth_headers(user, settings))

    assert response.status_code == 403


async def test_list_invites_returns_newest_first_with_status(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    """`created_at` is set explicitly: within one test transaction `now()` is constant."""
    headers = await admin_headers(db_session, settings)
    await create_invite(db_session, "pending@example.com", created_at=NOW - timedelta(hours=3))
    await create_invite(
        db_session,
        "used@example.com",
        created_at=NOW - timedelta(hours=2),
        used_at=NOW - timedelta(days=2),
        expires_at=NOW - timedelta(days=1),  # used wins over expired
    )
    await create_invite(
        db_session,
        "expired@example.com",
        created_at=NOW - timedelta(hours=1),
        expires_at=NOW - timedelta(minutes=1),
    )

    response = await api_client.get("/admin/invites", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert (body["limit"], body["offset"]) == (20, 0)
    assert [(i["email"], i["status"]) for i in body["items"]] == [
        ("expired@example.com", "expired"),
        ("used@example.com", "used"),
        ("pending@example.com", "pending"),
    ]
    assert "code_hash" not in body["items"][0]


async def test_list_invites_paginates_with_limit_and_offset(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    for n in range(5):  # invite-0 is the oldest, invite-4 the newest
        await create_invite(
            db_session, f"invite-{n}@example.com", created_at=NOW - timedelta(hours=5 - n)
        )

    response = await api_client.get("/admin/invites?limit=2&offset=1", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert (body["limit"], body["offset"]) == (2, 1)
    assert [i["email"] for i in body["items"]] == ["invite-3@example.com", "invite-2@example.com"]


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1"])
async def test_list_invites_rejects_out_of_range_pagination(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings, query: str
) -> None:
    headers = await admin_headers(db_session, settings)

    response = await api_client.get(f"/admin/invites?{query}", headers=headers)

    assert response.status_code == 422


# --- POST /admin/invites --------------------------------------------------------------------


async def test_create_invite_forbids_non_admin(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    user = await create_user(db_session, "user@example.com", role=UserRole.USER)

    response = await api_client.post(
        "/admin/invites", json={"email": "new@example.com"}, headers=auth_headers(user, settings)
    )

    assert response.status_code == 403


async def test_create_invite_returns_code_that_registers(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    admin = await create_user(db_session, "admin@example.com", role=UserRole.ADMIN)

    response = await api_client.post(
        "/admin/invites", json={"email": "New@Example.com"}, headers=auth_headers(admin, settings)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["status"] == "pending"
    assert body["created_by"] == str(admin.id)
    assert "code_hash" not in body

    register = await api_client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": PASSWORD, "invite_code": body["code"]},
    )
    assert register.status_code == 201


async def test_create_invite_expires_in_seven_days_by_default(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)

    response = await api_client.post(
        "/admin/invites", json={"email": "new@example.com"}, headers=headers
    )

    assert response.status_code == 201
    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    assert abs(expires_at - (datetime.now(UTC) + timedelta(days=7))) < timedelta(minutes=1)


async def test_create_invite_uses_expires_in_days(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)

    response = await api_client.post(
        "/admin/invites", json={"email": "new@example.com", "expires_in_days": 30}, headers=headers
    )

    assert response.status_code == 201
    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    assert abs(expires_at - (datetime.now(UTC) + timedelta(days=30))) < timedelta(minutes=1)


@pytest.mark.parametrize("days", [0, 31])
async def test_create_invite_rejects_out_of_range_expiry(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings, days: int
) -> None:
    headers = await admin_headers(db_session, settings)

    response = await api_client.post(
        "/admin/invites",
        json={"email": "new@example.com", "expires_in_days": days},
        headers=headers,
    )

    assert response.status_code == 422


async def test_create_invite_rejects_registered_email(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    await create_user(db_session, "taken@example.com")

    response = await api_client.post(
        "/admin/invites", json={"email": "taken@example.com"}, headers=headers
    )

    assert response.status_code == 409


async def test_create_invite_keeps_older_pending_invites(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    old_code = await create_invite(db_session, "new@example.com")

    response = await api_client.post(
        "/admin/invites", json={"email": "new@example.com"}, headers=headers
    )

    assert response.status_code == 201
    assert response.json()["code"] != old_code
    count = await db_session.scalar(
        select(func.count()).select_from(Invite).where(Invite.email == "new@example.com")
    )
    assert count == 2


# --- DELETE /admin/invites/{id} -------------------------------------------------------------


async def test_revoke_invite_deletes_it(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    await create_invite(db_session, "new@example.com")
    invite_id = await db_session.scalar(select(Invite.id))

    response = await api_client.delete(f"/admin/invites/{invite_id}", headers=headers)

    assert response.status_code == 204
    assert await db_session.scalar(select(Invite.id)) is None


async def test_revoke_invite_allows_expired(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    await create_invite(
        db_session, "new@example.com", expires_at=datetime.now(UTC) - timedelta(days=1)
    )
    invite_id = await db_session.scalar(select(Invite.id))

    response = await api_client.delete(f"/admin/invites/{invite_id}", headers=headers)

    assert response.status_code == 204


async def test_revoke_invite_returns_404_for_unknown_id(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)

    response = await api_client.delete(f"/admin/invites/{uuid.uuid4()}", headers=headers)

    assert response.status_code == 404


async def test_revoke_invite_rejects_used_invite(
    api_client: httpx2.AsyncClient, db_session: AsyncSession, settings: Settings
) -> None:
    headers = await admin_headers(db_session, settings)
    await create_invite(db_session, "new@example.com", used_at=datetime.now(UTC))
    invite_id = await db_session.scalar(select(Invite.id))

    response = await api_client.delete(f"/admin/invites/{invite_id}", headers=headers)

    assert response.status_code == 409
    assert await db_session.scalar(select(Invite.id)) == invite_id
