"""ORM models. Import every model module here so `Base.metadata` sees all tables
(Alembic's env.py imports this package for autogenerate)."""

from app.models import invite, posting, profile, user  # noqa: F401
