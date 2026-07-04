import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.genai.types import Content, Part
from orchestrator.persistence.database_services import DatabaseSessionService, DBSession

@pytest.fixture
def mock_engine():
    with patch("orchestrator.persistence.database_services.create_async_engine") as mock_create:
        engine = MagicMock() # Use MagicMock for the engine itself
        mock_create.return_value = engine
        
        # Setup engine.begin() as an async context manager
        conn_mock = AsyncMock()
        engine.begin.return_value.__aenter__ = AsyncMock(return_value=conn_mock)
        engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)
        
        yield engine

@pytest.fixture
def mock_session_factory():
    with patch("orchestrator.persistence.database_services.async_sessionmaker") as mock_maker:
        session_factory = MagicMock()
        session_instance = AsyncMock()
        
        # Setup context manager for async with session_factory()
        session_factory.return_value.__aenter__.return_value = session_instance
        session_factory.return_value.__aexit__.return_value = None
        
        mock_maker.return_value = session_factory
        yield session_factory, session_instance

@pytest.mark.asyncio
async def test_create_session(mock_engine, mock_session_factory):
    factory, session_instance = mock_session_factory
    service = DatabaseSessionService("postgresql+asyncpg://user:pass@localhost/db")
    
    session = await service.create_session(app_name="test_app", user_id="user_1", session_id="sesh_1")
    
    assert session.id == "sesh_1"
    session_instance.add.assert_called_once()
    session_instance.commit.assert_called_once()

@pytest.mark.asyncio
async def test_get_session(mock_engine, mock_session_factory):
    factory, session_instance = mock_session_factory
    service = DatabaseSessionService("postgresql+asyncpg://user:pass@localhost/db")
    
    # Mock execute result
    mock_result = MagicMock()
    db_entry = DBSession(
        id="sesh_1",
        app_name="test_app",
        user_id="user_1",
        state={},
        last_update_time=123.456,
        events=[]
    )
    mock_result.scalar_one_or_none.return_value = db_entry
    session_instance.execute.return_value = mock_result
    
    session = await service.get_session(app_name="test_app", user_id="user_1", session_id="sesh_1")
    
    assert session is not None
    assert session.id == "sesh_1"
    assert session.app_name == "test_app"

@pytest.mark.asyncio
async def test_append_event(mock_engine, mock_session_factory):
    factory, session_instance = mock_session_factory
    service = DatabaseSessionService("postgresql+asyncpg://user:pass@localhost/db")
    
    session = Session(app_name="test_app", user_id="user_1", id="sesh_1")
    event = Event(author="user", timestamp=123.456, content=Content(parts=[Part(text="hello")]))
    
    # Mock finding the session to update
    mock_result = MagicMock()
    db_entry = MagicMock(spec=DBSession)
    mock_result.scalar_one_or_none.return_value = db_entry
    session_instance.execute.return_value = mock_result
    
    await service.append_event(session, event)
    
    assert len(session.events) == 1
    session_instance.commit.assert_called_once()
