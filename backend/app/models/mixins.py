"""Columns shared by every table. Mix into a model: `class Posting(UUIDPrimaryKeyMixin, ..., Base)`.

A mixin is a plain class (not a Base subclass); SQLAlchemy copies its `mapped_column`s into
each model that inherits it. TypeORM parallel: an abstract base entity with
`@PrimaryGeneratedColumn` / `@CreateDateColumn` that entities extend.

Reading a column declaration:
    name: Mapped[python_type] = mapped_column(sql_type, **options)
- `Mapped[...]` is the Python type and decides NOT NULL: `Mapped[str]` → NOT NULL,
  `Mapped[str | None]` → nullable. No `nullable=` needed
- The SQL type can be omitted when SQLAlchemy can infer it (`uuid.UUID` → UUID)
- `server_default=` is rendered into the table DDL, so Postgres fills the value in
  (`DEFAULT gen_random_uuid()`); `func.<name>()` builds an SQL function call
- `sort_order=`: mixin columns would otherwise land after the model's own columns.
  Lower = further left, default 0
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid(), sort_order=-10
    )


class TimestampMixin:
    __mapper_args__ = {"eager_defaults": True}

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), sort_order=10
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now(),
        sort_order=10,
    )
