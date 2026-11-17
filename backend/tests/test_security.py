"""Tests for `app/security.py`: plain functions, no database or HTTP."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    generate_invite_code,
    hash_invite_code,
    hash_password,
    verify_password,
)

# --- Passwords ------------------------------------------------------------------------------


def test_hash_password_verifies_and_is_not_plaintext() -> None:
    hashed = hash_password("correct horse")

    assert hashed != "correct horse"
    assert hashed.startswith("$argon2")
    assert verify_password("correct horse", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    assert verify_password("wrong", hash_password("correct horse")) is False


def test_hash_password_is_salted() -> None:
    """Same password, different hashes: equal passwords can't be spotted in the table."""
    assert hash_password("same") != hash_password("same")


# --- Access tokens --------------------------------------------------------------------------


def test_access_token_round_trips_user_id(settings: Settings) -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id, settings)

    assert decode_access_token(token, settings) == user_id


def test_access_token_expires_after_configured_minutes(settings: Settings) -> None:
    token = create_access_token(uuid.uuid4(), settings)

    claims = jwt.decode(token, options={"verify_signature": False})
    expected = datetime.now(UTC) + timedelta(minutes=settings.jwt_expires_minutes)

    assert abs(claims["exp"] - expected.timestamp()) < 5


def test_expired_access_token_is_rejected(settings: Settings) -> None:
    expired = settings.model_copy(update={"jwt_expires_minutes": -1})
    token = create_access_token(uuid.uuid4(), expired)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, settings)


def test_access_token_with_other_secret_is_rejected(settings: Settings) -> None:
    # `model_copy` doesn't validate, so pass a `SecretStr` (a plain str would stay a str).
    other_secret = SecretStr("another-secret-that-is-also-32-chars-long")
    other = settings.model_copy(update={"jwt_secret": other_secret})
    token = create_access_token(uuid.uuid4(), other)

    with pytest.raises(jwt.InvalidSignatureError):
        decode_access_token(token, settings)


def test_token_with_other_audience_is_rejected(settings: Settings) -> None:
    """Correct secret, but issued for another purpose: must not work as an access token."""
    token = _sign(settings, sub=str(uuid.uuid4()), aud="invite")

    with pytest.raises(jwt.InvalidAudienceError):
        decode_access_token(token, settings)


def test_token_with_non_uuid_subject_is_rejected(settings: Settings) -> None:
    token = _sign(settings, sub="not-a-uuid", aud="access")

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, settings)


def _sign(settings: Settings, **claims: object) -> str:
    """Sign arbitrary claims with the test secret (valid for one hour)."""
    payload = {"exp": datetime.now(UTC) + timedelta(hours=1), **claims}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


# --- Invite codes ---------------------------------------------------------------------------


def test_generate_invite_code_is_random_and_url_safe() -> None:
    code = generate_invite_code()

    assert len(code) >= 40
    assert code != generate_invite_code()
    assert all(c.isalnum() or c in "-_" for c in code)


def test_hash_invite_code_is_deterministic_sha256_hex() -> None:
    code = generate_invite_code()

    hashed = hash_invite_code(code)

    assert hashed == hash_invite_code(code)
    assert len(hashed) == 64
    assert hashed != code
