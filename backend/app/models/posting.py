"""`postings` table: one submitted job posting and its extraction result."""

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class PostingStatus(StrEnum):
    """`StrEnum` members are real strings: `PostingStatus.PENDING == "pending"` is True,
    and they serialize to JSON as plain strings (a TS string enum)."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Posting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "postings"

    source: Mapped[str] = mapped_column(Text)

    raw_text: Mapped[str] = mapped_column(Text)

    status: Mapped[PostingStatus] = mapped_column(
        Enum(
            PostingStatus,
            name="posting_status",
            native_enum=False,
            create_constraint=True,
            length=32,
            values_callable=lambda e: [m.value for m in e],
        ),
        server_default=PostingStatus.PENDING.value,
    )

    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    error: Mapped[str | None] = mapped_column(Text)
