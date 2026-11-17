"""`invites` table: single-use registration codes issued by admins."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Invite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An invitation for one email address to register.

    Only the SHA-256 hash of the code is stored; the plain code is shown once, when the
    invite is created. Status is derived, not stored: `used_at` set → used;
    `expires_at` in the past → expired; otherwise pending.
    """

    __tablename__ = "invites"

    code_hash: Mapped[str] = mapped_column(Text, unique=True)

    email: Mapped[str] = mapped_column(Text)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    used_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
