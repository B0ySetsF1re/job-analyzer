"""Invites, managed by admins."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import Conflict, EmailTaken, NotFound
from app.models.invite import Invite
from app.models.user import User
from app.schemas import InviteCreate, PaginationParams
from app.security import generate_invite_code, hash_invite_code


class InviteService:
    """Invite queries and changes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, pagination: PaginationParams) -> tuple[list[Invite], int]:
        """One page of invites, newest first, and the total count across all pages."""
        total = await self.session.scalar(select(func.count()).select_from(Invite))
        invites = await self.session.scalars(
            select(Invite)
            .order_by(Invite.created_at.desc(), Invite.id.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        return list(invites), total or 0

    async def create(self, data: InviteCreate, admin: User) -> tuple[Invite, str]:
        """Issue an invite for `data.email`, created by `admin`.

        Older pending invites for the same email are kept; each code works until it's
        used or expires.

        Returns:
            The stored invite and its plain code. Only the hash is stored, so this is the
            one chance to show the code.

        Raises:
            EmailTaken: an account with this email already exists.
        """
        existing_id = await self.session.scalar(select(User.id).where(User.email == data.email))

        if existing_id is not None:
            raise EmailTaken

        code = generate_invite_code()
        code_hash = hash_invite_code(code)

        expires_at = datetime.now(UTC) + timedelta(days=data.expires_in_days)
        invite = Invite(
            code_hash=code_hash, email=data.email, created_by=admin.id, expires_at=expires_at
        )

        self.session.add(invite)

        await self.session.commit()

        return invite, code

    async def revoke(self, invite_id: uuid.UUID) -> None:
        """Delete an unused invite, so its code stops working. Expired ones can be revoked.

        Raises:
            NotFound: no invite with this id.
            Conflict: the invite was already used (keep it as a record of who joined).
        """
        invite = await self.session.get(Invite, invite_id)

        if invite is None:
            raise NotFound("Invite not found")
        if invite.used_at is not None:
            raise Conflict("Invite already used")

        await self.session.delete(invite)
        await self.session.commit()
