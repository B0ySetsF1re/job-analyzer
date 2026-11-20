"""Request and response bodies of the `/admin/invites` endpoints."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field


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
