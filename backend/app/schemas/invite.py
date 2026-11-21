"""Request and response bodies of the `/admin/invites` endpoints."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.schemas.auth import Email

DEFAULT_INVITE_DAYS = 7
MAX_INVITE_DAYS = 30


class InviteStatus(StrEnum):
    """Derived from the timestamps, not stored (see `Invite`)."""

    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class InviteRead(BaseModel):
    """An invite as returned by the API. Never includes the code or its hash."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_by: uuid.UUID | None
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None
    used_by: uuid.UUID | None

    # `@computed_field` + `@property`: calculated on serialization and included in the
    # JSON and the OpenAPI schema, like a stored field (≈ class-transformer
    # `@Expose() get status()`). A used invite stays "used" after its expiry date.
    @computed_field
    @property
    def status(self) -> InviteStatus:
        """`used` if redeemed, else `expired` if past `expires_at`, else `pending`."""
        if self.used_at is not None:
            return InviteStatus.USED
        if self.expires_at <= datetime.now(UTC):
            return InviteStatus.EXPIRED
        return InviteStatus.PENDING


class InviteCreate(BaseModel):
    """Body of `POST /admin/invites`. Out-of-range `expires_in_days` → automatic 422."""

    email: Email
    expires_in_days: int = Field(default=DEFAULT_INVITE_DAYS, ge=1, le=MAX_INVITE_DAYS)


class InviteCreated(InviteRead):
    """Response of `POST /admin/invites`: the invite plus its plain code, shown only here.

    Subclassing reuses every field of `InviteRead` (≈ TS `interface InviteCreated extends
    InviteRead`). The code isn't stored on the ORM row, so the route adds it next to the
    row's fields (see `create_invite` in `app/api/admin.py`).
    """

    code: str
