from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import URL, create_engine

import app.models  # noqa: F401  (registers all models on Base.metadata)
from app.db import Base


def test_migrations_match_models(test_database_url: URL) -> None:
    """Fails when a model changed but no migration was generated for it.

    Same diff `make migration` computes: the test DB (built from migrations) vs the models.
    Fix: `make migration MSG="..."`, review the file, rerun the tests.
    """
    # Sync engine: Alembic's comparison API is synchronous (psycopg supports both modes).
    engine = create_engine(test_database_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()

    assert diff == [], f"Models and migrations differ, run `make migration`:\n{diff}"
