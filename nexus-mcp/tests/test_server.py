import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

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
from mcp.server.fastmcp import Context  # noqa: E402
from mcp.server.session import ServerSession  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from database import User, engine  # noqa: E402
from server import delete_user, get_system_status, search_directory  # noqa: E402

# Tokens understood by nexus_common.IdentityContext's mock JWT parsing:
# "Bearer <id>" (no dots) yields user_id == "<id>".
ADMIN_AUTH_HEADER = "Bearer mock_user_123"
NON_ADMIN_AUTH_HEADER = "Bearer intruder_456"


def _mock_context(auth_header: str | None = None) -> Context[ServerSession, None]:
    """
    Builds a minimal stand-in for FastMCP's per-request Context.

    EDUCATIONAL NOTE: server._get_identity_from_context only touches
    `ctx.request_context.headers`, so a SimpleNamespace duck-type is enough —
    no MCP transport or real HTTP request is involved. The cast keeps mypy
    happy while making the mocking boundary explicit.
    """
    headers: dict[str, str] = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header
    fake = SimpleNamespace(request_context=SimpleNamespace(headers=headers))
    return cast("Context[ServerSession, None]", fake)


def teardown_module(module: object) -> None:
    """Clean up the physical temporary database file after all tests finish."""
    db_path = Path(test_db_path)
    if db_path.exists():
        db_path.unlink()


def test_init_db() -> None:
    """
    Verifies that the database is initialized properly and populated
    with the default set of 4 mock users.
    """
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        assert len(users) == 4
        names = [u.name for u in users]
        assert "Alice Smith" in names


def test_search_directory_no_criteria() -> None:
    """Searching with no criteria should return everyone."""
    results = search_directory()
    assert "HR Directory Results:" in results
    assert "Alice Smith" in results
    assert "Diana Prince" in results


def test_search_directory_by_department() -> None:
    """Verify department filtering."""
    results = search_directory(department="Engineering")
    assert "Alice Smith" in results
    assert "Charlie Brown" in results
    assert "Bob Jones" not in results


def test_search_directory_by_name() -> None:
    """Verify name (partial) filtering."""
    results = search_directory(name="Smith")
    assert "Alice Smith" in results
    assert "Charlie Brown" not in results


def test_search_directory_by_both() -> None:
    """Verify applying both department and name filtering simultaneously."""
    results = search_directory(department="Engineering", name="Alice")
    assert "Alice Smith" in results
    assert "Charlie Brown" not in results


def test_search_directory_no_results() -> None:
    """Verify the behavior when a search yields no results."""
    results = search_directory(department="NonExistent")
    assert results == "No employees found matching the criteria."


def test_get_system_status() -> None:
    """Verify the status resource."""
    status = get_system_status()
    assert "All systems operational" in status


def test_delete_user_as_admin() -> None:
    """
    An admin caller (mock_user_123) may delete users.

    We insert a throwaway user and delete it, so the seeded 4-user dataset
    that test_init_db asserts on is left untouched regardless of test order.
    """
    with Session(engine) as session:
        session.add(User(name="Temp Target", department="QA", email="temp@company.com"))
        session.commit()

    result = delete_user("temp@company.com", _mock_context(ADMIN_AUTH_HEADER))
    assert "Successfully deleted user temp@company.com" in result

    with Session(engine) as session:
        statement = select(User).where(User.email == "temp@company.com")
        assert session.exec(statement).first() is None


def test_delete_user_as_admin_not_found() -> None:
    """Deleting a nonexistent email reports 'not found' rather than failing."""
    result = delete_user("ghost@company.com", _mock_context(ADMIN_AUTH_HEADER))
    assert "not found" in result


def test_delete_user_denied_for_non_admin() -> None:
    """A non-admin identity must be refused, and the row must survive."""
    result = delete_user("bob@company.com", _mock_context(NON_ADMIN_AUTH_HEADER))
    assert "PERMISSION DENIED" in result
    assert "intruder_456" in result

    with Session(engine) as session:
        statement = select(User).where(User.email == "bob@company.com")
        assert session.exec(statement).first() is not None


def test_delete_user_denied_without_auth_header() -> None:
    """No Authorization header means 'anonymous', which is not an admin."""
    result = delete_user("bob@company.com", _mock_context(None))
    assert "PERMISSION DENIED" in result
    assert "anonymous" in result
