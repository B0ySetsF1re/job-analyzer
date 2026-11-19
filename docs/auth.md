# Auth

## Overview

Multi-user with invite-only registration and role-based access (`user`, `admin`).

- **Authentication:** `POST /auth/login` returns a JWT access token; clients send it as
  `Authorization: Bearer <jwt>`. No refresh tokens or cookies yet (see the Plan in CLAUDE.md)
- **Registration:** needs an invite code issued by an admin, single-use, bound to one email
- **Authorization:** roles (RBAC) decide which endpoints a user may call; ownership
  (`user_id` on every query) decides which rows. Another user's row → `404`

| Here | NestJS parallel |
|---|---|
| `app/security.py` (hashing, JWT) | `bcrypt` + `JwtService` |
| `get_current_user` dependency (1c.3) | Passport JWT strategy + `AuthGuard('jwt')` |
| `require_role(...)` dependency factory (1d) | `@Roles()` + `RolesGuard` |

---

## Structure

```
backend/
  app/
    security.py         # password hashing, JWT access tokens, invite codes (pure functions)
    config.py           # jwt_secret, jwt_expires_minutes
    api/
      deps.py           # SessionDep, SettingsDep, get_current_user, CurrentUser
      auth.py           # /auth router: register, login, me
    schemas/
      auth.py           # RegisterRequest, LoginRequest, TokenResponse, UserRead
    models/
      user.py           # User, UserRole (table `users`)
      invite.py         # Invite (table `invites`)
  tests/
    test_security.py    # unit tests, no DB
    test_auth_api.py    # HTTP tests through api_client
```

---

## Endpoints

| Endpoint | Success | Failures |
|---|---|---|
| `POST /auth/register` | `201` + `UserRead` | `400` any invite problem (one message), `409` email taken, `422` invalid body |
| `POST /auth/login` | `200` + `{access_token, token_type}` | `401` unknown email / wrong password / inactive (one message) |
| `GET /auth/me` | `200` + `UserRead` | `401` (+ `WWW-Authenticate: Bearer`) |

- **Generic errors on purpose:** a single message per endpoint doesn't tell a guesser which
  check failed (which emails exist, whether a code was ever valid)
- **Equal timing:** login verifies against `dummy_password_hash()` when the email is
  unknown, so "unknown email" isn't measurably faster than "wrong password"
- **Atomic redeem:** `UPDATE invites ... WHERE id = :id AND used_at IS NULL RETURNING id`.
  Two concurrent registrations can both pass the checks; only one gets a row back
- **Emails are lowercased** by the `Email` type in `app/schemas/auth.py`

## `get_current_user` / `CurrentUser`

```python
@router.get("/me")
async def me(user: CurrentUser) -> UserRead: ...
```

`CurrentUser = Annotated[User, Depends(get_current_user)]`: reads the Bearer header
(`HTTPBearer`), decodes the token, loads the user, and raises the same 401 for a missing,
invalid or expired token and for a deleted or inactive user. NestJS parallel:
`@UseGuards(AuthGuard('jwt'))` + a `@CurrentUser()` param decorator.

## CPU-heavy calls in async handlers

argon2 is slow on purpose (tens of ms of CPU). Called directly in an `async def` handler,
it blocks the event loop, and every other request waits. Run it in a worker thread:

```python
password_hash = await run_in_threadpool(hash_password, body.password)
```

Node's `bcrypt` does the same internally (libuv thread pool).

---

## Passwords

- **argon2** via `pwdlib` (`PasswordHash.recommended()`), the modern successor to bcrypt:
  slow and memory-hard on purpose, so leaked hashes are expensive to brute-force
- The hash string carries its own salt and parameters (`$argon2id$v=19$m=...`), so it's
  one column (`users.password_hash`) and the same password hashes differently each time

## Access tokens (JWT)

- **HS256**, signed with `JWT_SECRET` (one shared secret; RS256 would only help if other
  services had to verify tokens without being able to sign them)
- Claims: `sub` = user id (string), `aud` = `"access"`, `exp` = now + `JWT_EXPIRES_MINUTES`
  (default 1 day)
- `decode_access_token` pins the algorithm list and checks signature, `exp` and `aud`.
  Every failure is a `jwt.InvalidTokenError` (subclasses: `ExpiredSignatureError`,
  `InvalidSignatureError`, `InvalidAudienceError`, ...)
- **Why `aud`:** any later token signed with the same secret for another purpose gets a
  different audience, so it can't be used to log in

## Invite codes

- `secrets.token_urlsafe(32)`: ~43 random URL-safe chars. `secrets`, never `random`
  (predictable, not for security)
- Stored as **SHA-256** (`invites.code_hash`), not argon2: the code is random and long, so
  it can't be guessed, and a deterministic hash allows `WHERE code_hash = ...` lookups
- The plain code is returned once, when the admin creates the invite

## Settings

| Env var | Default | Notes |
|---|---|---|
| `JWT_SECRET` | — (required) | Min 32 chars, `SecretStr`. Generate: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_EXPIRES_MINUTES` | `1440` | Access token lifetime |

`SecretStr` prints as `**********` (logs, reprs, tracebacks); read it with
`.get_secret_value()`.

---

## Gotchas

### `ValidationError: jwt_secret Field required` on `make test` / `make dev`
- **Cause:** `JWT_SECRET` is missing from your `.env` (`make install` only creates `.env`
  when it doesn't exist, so an older `.env` lacks new variables)
- **Fix:** add `JWT_SECRET=...` (see Settings). The `api` container gets it via
  `docker-compose.yml`, which reads the same `.env`

### `TypeError: Object of type UUID is not JSON serializable` when creating a token
- The payload is serialized with `json`, which doesn't know `uuid.UUID`. PyJWT also
  requires `sub` to be a string (non-strings fail on decode with `InvalidSubjectError`)
- **Fix:** `str(user_id)` when encoding, `uuid.UUID(payload["sub"])` when decoding
