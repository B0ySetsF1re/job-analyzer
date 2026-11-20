"""`/auth` endpoints: register with an invite code, log in, get the current user.

Thin routes: logic lives in `AuthService`; its `DomainError`s become HTTP errors through
the handler in `app/main.py`.
"""

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentUser
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, auth: AuthServiceDep) -> UserRead:
    """Create an account (role `user`) with a single-use invite code bound to the email."""
    user = await auth.register(body)
    return UserRead.model_validate(user)


@router.post("/login")
async def login(body: LoginRequest, auth: AuthServiceDep) -> TokenResponse:
    """Exchange email + password for a JWT access token."""
    return TokenResponse(access_token=await auth.login(body))


@router.get("/me")
async def me(user: CurrentUser) -> UserRead:
    """The logged-in user. `CurrentUser` already returned 401 if the token is bad."""
    return UserRead.model_validate(user)
