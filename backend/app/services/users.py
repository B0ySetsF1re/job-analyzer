"""User accounts: admin management (and, next, the `/admin/users` endpoints)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.security import hash_password


class UserService:
    """User queries and changes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_or_promote_admin(self, email: str, password: str) -> bool:
        """Make `email` an active admin with `password`; return True if the user was created.

        An existing user is promoted: role `admin`, reactivated, and the password is
        replaced by the new one, so this also recovers a locked-out admin. `email` and
        `password` must already be validated.
        """
        user = await self.session.scalar(select(User).where(User.email == email))

        # Called from the CLI only: no event loop shared with requests, so no thread pool.
        password_hash = hash_password(password)

        if user is None:
            self.session.add(User(email=email, password_hash=password_hash, role=UserRole.ADMIN))
            created = True
        else:
            user.role = UserRole.ADMIN
            user.is_active = True
            user.password_hash = password_hash
            created = False

        await self.session.commit()
        return created
