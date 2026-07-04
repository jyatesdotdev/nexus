import pytest
import logging
from typing import Tuple, Generator
from unittest.mock import AsyncMock, patch, MagicMock

# EDUCATIONAL NOTE: Testing Persistence Layer
# We use AsyncMock and patch to isolate our tests from the actual database.
# By mocking the AsyncEngine and AsyncSession, we can verify SQL execution
# logic without requiring a running PostgreSQL container or risking side effects.

from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.genai.types import Content, Part
from orchestrator.persistence.postgres_services import PostgresMemoryService, DBMemoryEntry

@pytest.fixture(autouse=True)
def mock_genai_client():
    with patch("orchestrator.persistence.postgres_services.get_genai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.models.embed_content.return_value = MagicMock(
            embeddings=[MagicMock(values=[0.1] * 768)]
        )
        yield mock_client

@pytest.fixture
def mock_engine() -> Generator[MagicMock, None, None]:
    with patch("orchestrator.persistence.postgres_services.create_async_engine") as mock_create:
        engine = MagicMock()
        mock_create.return_value = engine
        
        # Setup engine.begin() as an async context manager
        conn_mock = AsyncMock()
        engine.begin.return_value.__aenter__ = AsyncMock(return_value=conn_mock)
        engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        yield engine

@pytest.fixture
def mock_session_factory() -> Generator[Tuple[MagicMock, AsyncMock], None, None]:
    with patch("orchestrator.persistence.postgres_services.async_sessionmaker") as mock_maker:
        session_factory = MagicMock()
        session_instance = AsyncMock()
        
        # Setup context manager for async with session_factory()
        session_factory.return_value.__aenter__.return_value = session_instance
        session_factory.return_value.__aexit__.return_value = None
        
        mock_maker.return_value = session_factory
        yield session_factory, session_instance

@pytest.mark.asyncio
async def test_add_session_to_memory(mock_engine: MagicMock, mock_session_factory: Tuple[MagicMock, AsyncMock]) -> None:
    factory, session_instance = mock_session_factory
    
    service = PostgresMemoryService("postgresql+asyncpg://user:pass@localhost/db")
    
    session = Session(app_name="test_app", user_id="user_1", id="session_1")
    event = Event(
        author="user",
        timestamp=1600000000.0,
        content=Content(parts=[Part(text="Hello Postgres")])
    )
    session.events.append(event)
    
    await service.add_session_to_memory(session)
    
    # Verify that initialize was called and session added
    assert mock_engine.begin.called
    session_instance.add.assert_called_once()
    session_instance.commit.assert_called_once()

@pytest.mark.asyncio
async def test_search_memory(mock_engine: MagicMock, mock_session_factory: Tuple[MagicMock, AsyncMock]) -> None:
    factory, session_instance = mock_session_factory
    
    service = PostgresMemoryService("postgresql+asyncpg://user:pass@localhost/db")
    
    # Mock the execute result
    mock_result = MagicMock()
    mock_entry = DBMemoryEntry()
    mock_entry.app_name = "test_app"
    mock_entry.user_id = "user_1"
    mock_entry.content = {"parts": [{"text": "Hello Postgres"}]}
    mock_entry.author = "user"
    mock_entry.timestamp = MagicMock()
    
    mock_entry.timestamp.isoformat.return_value = "2023-01-01T00:00:00"
    mock_result.scalars().all.return_value = [mock_entry]
    session_instance.execute.return_value = mock_result
    
    response = await service.search_memory(app_name="test_app", user_id="user_1", query="Hello")
    
    assert len(response.memories) == 1
    assert response.memories[0].author == "user"
