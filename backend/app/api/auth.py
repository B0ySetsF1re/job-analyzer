"""`/auth` endpoints: register with an invite code, log in, get the current user."""

from fastapi import APIRouter, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select, update

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.models.invite import Invite
from app.models.user import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.security import (
    create_access_token,
    dummy_password_hash,
    hash_invite_code,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def invalid_invite() -> HTTPException:
    """One 400 for every invite problem (unknown, used, expired, other email).

    A single message means the response doesn't tell a guesser which check failed.
    """
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid or expired invite code")


def invalid_credentials() -> HTTPException:
    """One 401 for unknown email, wrong password and inactive account."""
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, session: SessionDep) -> UserRead:
    """Create an account (role `user`) with a single-use invite code bound to the email."""
    invite = await session.scalar(
        select(Invite).where(
            Invite.code_hash == hash_invite_code(body.invite_code),
            Invite.used_at.is_(None),
            Invite.expires_at > func.now(),
            Invite.email == body.email,
        )
    )

    if invite is None:
        raise invalid_invite()

    existing_id = await session.scalar(select(User.id).where(User.email == body.email))

    if existing_id:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")

    password_hash = await run_in_threadpool(hash_password, body.password)

    user = User(email=body.email, password_hash=password_hash)
    session.add(user)

    await session.flush()

    result = await session.execute(
        update(Invite)
        .where(Invite.id == invite.id, Invite.used_at.is_(None))
        .values(used_at=func.now(), used_by=user.id)
        .returning(Invite.id)
    )

    redeemed_id = result.scalar_one_or_none()

    if not redeemed_id:
        raise invalid_invite()

    await session.commit()

    return UserRead.model_validate(user)


@router.post("/login")
async def login(body: LoginRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    """Exchange email + password for a JWT access token."""
    user = await session.scalar(select(User).where(User.email == body.email))

    if user is None:
        await run_in_threadpool(verify_password, body.password, dummy_password_hash())
        raise invalid_credentials()

    is_password_valid = await run_in_threadpool(verify_password, body.password, user.password_hash)

    if not is_password_valid or not user.is_active:
        raise invalid_credentials()

    return TokenResponse(access_token=create_access_token(user.id, settings))


@router.get("/me")
async def me(user: CurrentUser) -> UserRead:
    """The logged-in user. `CurrentUser` already returned 401 if the token is bad."""
    return UserRead.model_validate(user)
