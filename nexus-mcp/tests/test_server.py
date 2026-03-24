import os
import tempfile
from pathlib import Path

# ==============================================================================
# EDUCATIONAL NOTE: Mocking External Dependencies for Tests
# When testing a system that interacts with an external database (e.g. Postgres),
# we do NOT want tests connecting to the real production or development database.
# Tests should be isolated, fast, and repeatable.
#
# To achieve this, we create a temporary file database specifically for the test
# session. We then set the `DATABASE_URL` environment variable BEFORE importing
# our application code (`server.py` and `database.py`). This guarantees that
# when `database.py` initializes the engine, it points to our test database.
# ==============================================================================

# Create a temporary file database for tests
fd, test_db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
TEST_DATABASE_URL = f"sqlite:///{test_db_path}"

# Inject the test database URL into the environment
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Now we can safely import our application modules.
# We suppress the E402 (module level import not at top of file) linter rule here
# because we MUST set the environment variable before these imports occur.
from sqlmodel import Session, select  # noqa: E402

from database import User, engine  # noqa: E402
from server import get_system_status, search_directory  # noqa: E402


def teardown_module(module):
    """Clean up the physical temporary database file after all tests finish."""
    db_path = Path(test_db_path)
    if db_path.exists():
        db_path.unlink()


def test_init_db():
    """
    Verifies that the database is initialized properly and populated
    with the default set of 4 mock users.
    """
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        assert len(users) == 4
        names = [u.name for u in users]
        assert "Alice Smith" in names


def test_search_directory_no_criteria():
    """Searching with no criteria should return everyone."""
    results = search_directory()
    assert "HR Directory Results:" in results
    assert "Alice Smith" in results
    assert "Diana Prince" in results


def test_search_directory_by_department():
    """Verify department filtering."""
    results = search_directory(department="Engineering")
    assert "Alice Smith" in results
    assert "Charlie Brown" in results
    assert "Bob Jones" not in results


def test_search_directory_by_name():
    """Verify name (partial) filtering."""
    results = search_directory(name="Smith")
    assert "Alice Smith" in results
    assert "Charlie Brown" not in results


def test_search_directory_by_both():
    """Verify applying both department and name filtering simultaneously."""
    results = search_directory(department="Engineering", name="Alice")
    assert "Alice Smith" in results
    assert "Charlie Brown" not in results


def test_search_directory_no_results():
    """Verify the behavior when a search yields no results."""
    results = search_directory(department="NonExistent")
    assert results == "No employees found matching the criteria."


def test_get_system_status():
    """Verify the status resource."""
    status = get_system_status()
    assert "All systems operational" in status
