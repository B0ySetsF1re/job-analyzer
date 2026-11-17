"""`users` table: accounts that can log in."""

from enum import StrEnum

from sqlalchemy import Boolean, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.types import str_enum


class UserRole(StrEnum):
    """Roles for RBAC. Every new account starts as `USER`; admins are promoted."""

    USER = "user"
    ADMIN = "admin"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An account. `email` is stored lowercased (the API schemas normalize it)."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(Text, unique=True)

    password_hash: Mapped[str] = mapped_column(Text)

    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole, name="user_role"), server_default=UserRole.USER.value
    )

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
