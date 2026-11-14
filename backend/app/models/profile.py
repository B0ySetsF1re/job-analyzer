"""`profiles` table: the uploaded CV and its parsed, structured form."""

from typing import Any

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Profile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profiles"

    raw_text: Mapped[str] = mapped_column(Text)

    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
