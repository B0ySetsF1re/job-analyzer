"""Dependencies shared by routers: DB session, settings, the current user.

Use the `Annotated` aliases as handler parameters, e.g. `user: CurrentUser`. FastAPI
resolves them per request (≈ NestJS providers + `@UseGuards(AuthGuard('jwt'))`).
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models.user import User
from app.security import decode_access_token

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

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
