"""Dependencies shared by routers: DB session, settings, the current user.

Use the `Annotated` aliases as handler parameters, e.g. `user: CurrentUser`. FastAPI
resolves them per request (≈ NestJS providers + `@UseGuards(AuthGuard('jwt'))`).
"""

from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models.user import User, UserRole
from app.schemas import PaginationParams
from app.security import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

# `?limit=&offset=` for list endpoints. `Query()` on a Pydantic model reads its fields from
# the query string (≈ a NestJS `@Query() dto: PaginationDto` with class-validator).
PaginationDep = Annotated[PaginationParams, Query()]

# Reads `Authorization: Bearer <token>` and adds the "Authorize" button to /docs.
# `auto_error=False`: a missing header gives `None` instead of raising inside HTTPBearer,
# so every auth failure goes through `unauthorized()`, one place that shapes the 401.
bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized() -> HTTPException:
    """The one 401 for every auth failure: no details about *why* it failed.

    `WWW-Authenticate: Bearer` tells the client which auth scheme the API expects
    (required by the HTTP spec for 401 responses).
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: SessionDep,
    settings: SettingsDep,
) -> User:
    """Resolve the logged-in user from the Bearer token, or fail with 401.

    Passport parallel: the JWT strategy's `validate()` + `AuthGuard('jwt')` in one function.
    """
    if not credentials:
        raise unauthorized()

    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except jwt.InvalidTokenError:
        raise unauthorized() from None

    user = await session.get(User, user_id)

    if not user or not user.is_active:
        raise unauthorized()

    return user


# Handler parameter for authenticated endpoints: `async def me(user: CurrentUser)`.
# ≈ `@UseGuards(AuthGuard('jwt'))` + a `@CurrentUser()` param decorator, in one alias.
CurrentUser = Annotated[User, Depends(get_current_user)]


def forbidden() -> HTTPException:
    """The 403 for an authenticated user whose role isn't allowed.

    401 = "who are you?" (no or bad token), 403 = "I know you, but no".
    """
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Build a dependency that lets only users with one of `roles` through.

    A dependency *factory*: it returns a new dependency function, configured by `roles`
    (≈ NestJS `@Roles('admin')` + `RolesGuard`, as one call). `*roles` collects any number
    of positional arguments into a tuple, like TS `...roles: UserRole[]`.

    Usage: `admin: Annotated[User, Depends(require_role(UserRole.ADMIN))]`, or the
    `AdminUser` alias below.
    """

    async def check_role(user: CurrentUser) -> User:
        if user.role not in roles:
            raise forbidden()

        return user

    return check_role


# Handler parameter for admin-only endpoints: `async def list_users(admin: AdminUser)`.
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
