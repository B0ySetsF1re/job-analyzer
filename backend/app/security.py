"""Security primitives: password hashing, JWT access tokens, invite codes.

Pure functions, no HTTP and no DB, so they're unit-tested on their own. The auth
endpoints and `get_current_user` (step 1c.3) are built on top of them.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache

import jwt
from pwdlib import PasswordHash

from app.config import Settings

JWT_ALGORITHM = "HS256"

# `aud` claim of access tokens. Decoding checks it, so a token signed with the same secret
# for another purpose (e.g. a future email-verification token) can't be used to log in.
ACCESS_TOKEN_AUDIENCE = "access"


@lru_cache
def get_password_hasher() -> PasswordHash:
    """Password hasher singleton, using pwdlib's recommended algorithm (argon2)."""
    return PasswordHash.recommended()


# --- Passwords ------------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password for storage in `users.password_hash`.

    Returns:
        An argon2 hash string (`$argon2id$...`) that includes its own random salt, so
        hashing the same password twice gives different strings.
    """
    return get_password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a login password against the stored hash."""
    return get_password_hasher().verify(password, password_hash)


# --- Access tokens (JWT) --------------------------------------------------------------------


def create_access_token(user_id: uuid.UUID, settings: Settings) -> str:
    """Issue a signed JWT for a logged-in user.

    Claims: `sub` (user id), `aud` (`ACCESS_TOKEN_AUDIENCE`), `exp` (now +
    `settings.jwt_expires_minutes`).
    """
    sub = str(user_id)
    exp = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {"sub": sub, "exp": exp, "aud": ACCESS_TOKEN_AUDIENCE}

    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    """Verify an access token and return the user id from its `sub` claim.

    Raises:
        jwt.InvalidTokenError: The token is malformed, expired, has a wrong signature or
            audience, or its `sub` is not a UUID. (Expired, bad signature and bad audience
            are all subclasses of it, so callers catch just this one.)
    """
    secret = settings.jwt_secret.get_secret_value()
    payload = jwt.decode(
        token,
        secret,
        algorithms=[JWT_ALGORITHM],
        audience=ACCESS_TOKEN_AUDIENCE,
        options={"require": ["exp", "sub"]},
    )

    try:
        return uuid.UUID(payload["sub"])
    except ValueError as err:
        raise jwt.InvalidTokenError("Invalid token sub value!") from err


# --- Invite codes ---------------------------------------------------------------------------


def generate_invite_code() -> str:
    """Create a new random, URL-safe invite code (shown to the admin once, never stored)."""
    return secrets.token_urlsafe(32)


def hash_invite_code(code: str) -> str:
    """SHA-256 hex digest of an invite code, as stored in `invites.code_hash`.

    Deterministic (same code → same hash), so registration can look the invite up with
    `WHERE code_hash = ...`. A fast hash is fine here, unlike for passwords: the code is
    random and long, so it can't be guessed.
    """
    return hashlib.sha256(code.encode()).hexdigest()
