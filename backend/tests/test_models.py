"""Tests for the ORM models in `app/models/`.

They run against the real test database (see the `db_session` fixture in conftest.py),
so they check what Postgres actually does: server defaults, the CHECK constraint on
`status`, JSONB storage. Each test runs in a transaction that is rolled back afterwards.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.posting import Posting, PostingStatus
from app.models.profile import Profile

pytestmark = pytest.mark.anyio


def make_posting(**overrides: object) -> Posting:
    """Build an unsaved `Posting` with valid required fields.

    Args:
        **overrides: Column values that replace or extend the defaults,
            e.g. `make_posting(status=PostingStatus.FAILED)`.

    Returns:
        A new, transient `Posting` (not added to any session).
    """
    fields: dict[str, object] = {
        "source": "linkedin",
        "raw_text": "Senior Python Engineer at Acme...",
    }
    return Posting(**(fields | overrides))


async def test_posting_gets_db_defaults_on_flush(db_session: AsyncSession) -> None:
    """Postgres fills in id, status, timestamps; nullable columns stay None.

    The values only exist after `flush()`: the INSERT runs with RETURNING and
    SQLAlchemy copies the server-generated values back onto the object.
    """
    posting = make_posting()
    db_session.add(posting)
    await db_session.flush()  # INSERT ... RETURNING fills in server-side defaults

    assert isinstance(posting.id, uuid.UUID)
    assert posting.status == PostingStatus.PENDING
    assert posting.extraction is None
    assert posting.error is None
    assert posting.created_at.tzinfo is not None  # timestamptz, not naive
    assert posting.updated_at.tzinfo is not None


async def test_posting_status_is_stored_as_lowercase_value(db_session: AsyncSession) -> None:
    """The DB stores the enum value ("processed"), not the member name ("PROCESSED").

    Guards `values_callable` on the `status` column; SQLAlchemy's default is the name.
    """
    db_session.add(make_posting(status=PostingStatus.PROCESSED))
    await db_session.flush()

    stored = await db_session.scalar(text("select status from postings"))

    assert stored == "processed"  # the enum value, not the member name "PROCESSED"


async def test_posting_status_rejects_unknown_values(db_session: AsyncSession) -> None:
    """The CHECK constraint rejects a status that isn't in `PostingStatus`.

    Uses raw SQL on purpose: it bypasses the Python enum, so only the database
    can stop the bad value. Fails if `create_constraint=True` is missing.
    """
    with pytest.raises(IntegrityError, match="ck_postings_posting_status"):
        await db_session.execute(
            text(
                "insert into postings (source, raw_text, status) "
                "values ('linkedin', 'text', 'archived')"
            )
        )


async def test_posting_extraction_round_trips_as_jsonb(db_session: AsyncSession) -> None:
    """A dict saved to `extraction` comes back equal, and the column type is `jsonb`.

    `expunge_all()` empties the session's identity map, so the read really goes to
    the database instead of returning the cached object.
    """
    extraction = {
        "company": "Acme",
        "salary_min": 90000,
        "required_skills": ["python", "postgres"],
        "relocation_required": False,
    }
    posting = make_posting(extraction=extraction)
    db_session.add(posting)
    await db_session.flush()
    db_session.expunge_all()  # forget cached objects, so the next read hits the DB

    loaded = await db_session.get(Posting, posting.id)
    column_type = await db_session.scalar(text("select pg_typeof(extraction)::text from postings"))

    assert loaded is not None
    assert loaded is not posting
    assert loaded.extraction == extraction
    assert column_type == "jsonb"


async def test_profile_insert_and_read_back(db_session: AsyncSession) -> None:
    """A `Profile` can be inserted and loaded back with all its fields."""
    profile = Profile(raw_text="10 years of backend...", data={"skills": ["python", "nestjs"]})
    db_session.add(profile)
    await db_session.flush()
    db_session.expunge_all()

    loaded = await db_session.scalar(select(Profile))

    assert loaded is not None
    assert loaded.id == profile.id
    assert loaded.raw_text == "10 years of backend..."
    assert loaded.data == {"skills": ["python", "nestjs"]}
    assert loaded.created_at.tzinfo is not None


async def test_posting_updated_at_is_readable_after_update(db_session: AsyncSession) -> None:
    """`updated_at` can be read right after an UPDATE without extra I/O.

    Guards `eager_defaults=True` on `TimestampMixin`. Without it the attribute is
    expired after the UPDATE, and reading it would need a lazy SELECT, which async
    SQLAlchemy forbids (`MissingGreenlet`).
    """
    posting = make_posting()
    db_session.add(posting)
    await db_session.flush()

    posting.status = PostingStatus.FAILED
    await db_session.flush()  # UPDATE ... RETURNING updated_at

    assert posting.updated_at.tzinfo is not None
