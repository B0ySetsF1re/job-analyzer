import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import sqlalchemy_url


def test_sqlalchemy_url_adds_psycopg_driver() -> None:
    url = sqlalchemy_url("postgresql://user:pass@localhost:5432/db")

    assert url.drivername == "postgresql+psycopg"
    assert url.render_as_string(hide_password=False) == (
        "postgresql+psycopg://user:pass@localhost:5432/db"
    )


@pytest.mark.anyio
async def test_db_session_uses_test_database(db_session: AsyncSession) -> None:
    """Guards against tests touching the dev database: `db_session` must use `<db>_test`."""
    db_name = await db_session.scalar(text("select current_database()"))

    assert db_name is not None
    assert db_name.endswith("_test")
