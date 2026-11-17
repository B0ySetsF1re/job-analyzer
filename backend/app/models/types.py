"""Reusable column types for the ORM models."""

from enum import StrEnum

from sqlalchemy import Enum


def str_enum[E: StrEnum](enum_cls: type[E], *, name: str) -> Enum:
    """VARCHAR + CHECK column type for a `StrEnum`, storing member values.

    Use for status- and role-like columns:
    `mapped_column(str_enum(PostingStatus, name="posting_status"), ...)`.
    Why not a native Postgres enum: see docs/database.md → Status.

    Args:
        enum_cls: The `StrEnum` whose values are allowed.
        name: Constraint name; the naming convention turns it into `ck_<table>_<name>`.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,  # VARCHAR + CHECK, not CREATE TYPE ... AS ENUM
        create_constraint=True,  # off by default: without it there is no CHECK
        length=32,  # room for new values (default = longest current value)
        values_callable=lambda e: [m.value for m in e],  # store "pending", not "PENDING"
    )
