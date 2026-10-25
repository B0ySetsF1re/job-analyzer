from app.db import sqlalchemy_url


def test_sqlalchemy_url_adds_psycopg_driver() -> None:
    url = sqlalchemy_url("postgresql://user:pass@localhost:5432/db")

    assert url.drivername == "postgresql+psycopg"
    assert url.render_as_string(hide_password=False) == (
        "postgresql+psycopg://user:pass@localhost:5432/db"
    )
