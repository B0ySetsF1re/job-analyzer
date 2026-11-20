"""Registration with an invite code and login."""

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.errors import EmailTaken, InvalidCredentials, InvalidInvite
from app.models.invite import Invite
from app.models.user import User
from app.schemas import LoginRequest, RegisterRequest
from app.security import (
    create_access_token,
    dummy_password_hash,
    hash_invite_code,
    hash_password,
    verify_password,
)


class AuthService:
    """Account creation and token issuing. Commits its own unit of work."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def register(self, data: RegisterRequest) -> User:
        """Create a `user`-role account and redeem its single-use invite atomically.

        Raises:
            InvalidInvite: unknown, used, expired or bound to another email.
            EmailTaken: an account with this email exists.
        """
        invite = await self.session.scalar(
            select(Invite).where(
                Invite.code_hash == hash_invite_code(data.invite_code),
                Invite.used_at.is_(None),
                Invite.expires_at > func.now(),
                Invite.email == data.email,
            )
        )
        if invite is None:
            raise InvalidInvite

        existing_id = await self.session.scalar(select(User.id).where(User.email == data.email))
        if existing_id:
            raise EmailTaken

        password_hash = await run_in_threadpool(hash_password, data.password)
        user = User(email=data.email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()

        # Conditional UPDATE: two concurrent registrations can both pass the check above;
        # only one gets a row back.
        result = await self.session.execute(
            update(Invite)
            .where(Invite.id == invite.id, Invite.used_at.is_(None))
            .values(used_at=func.now(), used_by=user.id)
            .returning(Invite.id)
        )
        if not result.scalar_one_or_none():
            raise InvalidInvite

        await self.session.commit()
        return user

    async def login(self, data: LoginRequest) -> str:
        """Return a JWT access token for valid credentials of an active user.

        Raises:
            InvalidCredentials: unknown email, wrong password or inactive account.
        """
        user = await self.session.scalar(select(User).where(User.email == data.email))

        if user is None:
            # Same argon2 work as a real check, so unknown emails aren't faster.
            await run_in_threadpool(verify_password, data.password, dummy_password_hash())
            raise InvalidCredentials

        is_password_valid = await run_in_threadpool(
            verify_password, data.password, user.password_hash
        )
        if not is_password_valid or not user.is_active:
            raise InvalidCredentials

        return create_access_token(user.id, self.settings)
