"""API tests for `GET /admin/invites`: access control, status, order, pagination."""

from datetime import UTC, datetime, timedelta

import httpx2
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.user import UserRole
from tests.helpers import admin_headers, auth_headers, create_invite, create_user

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
