"""Invites, managed by admins."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import Invite
from app.schemas import PaginationParams


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
