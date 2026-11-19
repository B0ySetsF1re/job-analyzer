"""Request and response bodies of the `/auth` endpoints (≈ NestJS DTOs)."""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole

# Validated email, lowercased, so `Alice@X.com` and `alice@x.com` are the same account.
# `AfterValidator` runs after `EmailStr` has checked the format (≈ a class-transformer
# `@Transform` after `@IsEmail`).
type Email = Annotated[EmailStr, AfterValidator(str.lower)]


class RegisterRequest(BaseModel):
    """Body of `POST /auth/register`."""

    email: Email
    password: str = Field(min_length=8, max_length=128)
    invite_code: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """Body of `POST /auth/login`.

    No length rules on `password`: a login form shouldn't reveal the password policy, a
    wrong password just fails with 401.
    """

    email: Email
    password: str


class TokenResponse(BaseModel):
    """Response of `POST /auth/login`. `token_type` follows the OAuth2 convention."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserRead(BaseModel):
    """A user as returned by the API. Never includes `password_hash`."""

    # Lets `UserRead.model_validate(user)` read attributes off the SQLAlchemy object
    # (≈ class-transformer `plainToInstance(UserRead, entity)`).
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
