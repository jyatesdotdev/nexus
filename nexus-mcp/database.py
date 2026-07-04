import os
from collections.abc import Generator

from sqlmodel import Field, Session, SQLModel, create_engine, select

# ==============================================================================
# EDUCATIONAL NOTE: Why SQLModel?
# SQLModel is built on top of SQLAlchemy and Pydantic. It allows us to define
# our database models and data validation rules in one single place.
# It makes the code cleaner, fully typed, and provides robust protection against
# SQL Injection compared to raw SQLite queries.
# ==============================================================================


class User(SQLModel, table=True):
    """
    Represents an employee in the HR directory.
    By inheriting from SQLModel with table=True, this class doubles as:
    1. A SQLAlchemy model for database schema generation and querying.
    2. A Pydantic model for data validation and serialization.
    """

    __tablename__ = "users"  # Explicitly naming the table is a good practice
    id: int | None = Field(default=None, primary_key=True)
    name: str
    department: str
    email: str


# ==============================================================================
# EDUCATIONAL NOTE: Externalizing Database Configuration
# Hardcoding database credentials or paths is a security risk and limits flexibility.
# By reading from an environment variable (DATABASE_URL), we allow this MCP server
# to connect to external, offsite databases (like PostgreSQL on AWS/GCP) in production.
# The 'sqlite:///hr.db' is merely a fallback for local development.
#
# Example usage for PostgreSQL:
# export DATABASE_URL="postgresql://username:password@remote-host:5432/hr_db"
# ==============================================================================
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///hr.db")

# For SQLite, we must set "check_same_thread": False because FastAPI/FastMCP
# handles requests concurrently in different threads. This argument is safely
# ignored if the connection is made to PostgreSQL.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# The 'engine' manages connection pooling and execution of SQL commands.
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def get_session() -> Generator[Session]:
    """
    Generator that provides a database session.
    It can be used as a dependency in FastAPI or simply with context managers.
    """
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """
    Initializes the database and populates it with mock data if it's empty.

    EDUCATIONAL NOTE: Schema Migration vs. create_all
    In this prototype, we use `SQLModel.metadata.create_all(engine)` to create
    the tables if they don't exist. This is convenient for quick startups.
    However, for production projects, you should rely on Alembic to manage
    incremental schema changes (migrations) rather than `create_all`.
    """
    SQLModel.metadata.create_all(engine)

    # Use a context manager to ensure the session is always closed properly
    with Session(engine) as session:
        # Check if the database is already populated
        user = session.exec(select(User)).first()
        if not user:
            print("Populating database with mock HR data...")
            users = [
                User(
                    name="Alice Smith",
                    department="Engineering",
                    email="alice@company.com",
                ),
                User(name="Bob Jones", department="Marketing", email="bob@company.com"),
                User(
                    name="Charlie Brown",
                    department="Engineering",
                    email="charlie@company.com",
                ),
                User(name="Diana Prince", department="HR", email="diana@company.com"),
            ]
            session.add_all(users)
            session.commit()
