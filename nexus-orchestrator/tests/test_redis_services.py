import pytest
from unittest.mock import AsyncMock

# EDUCATIONAL NOTE: Testing Distributed Caching
# We mock the Redis client to verify key-value storage and retrieval logic.
# This ensures our session management and memory search logic is correct
# while remaining 100% isolated from external infrastructure.

from google.adk.sessions.session import Session
from google.adk.events.event import Event
from google.genai.types import Content, Part
from orchestrator.persistence.redis_services import RedisSessionService, RedisMemoryService

@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()

@pytest.mark.asyncio
async def test_redis_session_service_create(mock_redis: AsyncMock) -> None:
    service = RedisSessionService(mock_redis)
    # Mock exists to return False (0)
    mock_redis.exists.return_value = 0
    
    session = await service.create_session(app_name="test_app", user_id="user_1", session_id="sesh_1")
    
    assert session.id == "sesh_1"
    mock_redis.set.assert_called_once()
    mock_redis.sadd.assert_called_once()

@pytest.mark.asyncio
async def test_redis_session_service_get(mock_redis: AsyncMock) -> None:
    service = RedisSessionService(mock_redis)
    session_instance = Session(app_name="test_app", user_id="user_1", id="sesh_1")
    session_json = session_instance.model_dump_json()
    mock_redis.get.return_value = session_json
    
    session = await service.get_session(app_name="test_app", user_id="user_1", session_id="sesh_1")
    assert session is not None
    assert session.id == "sesh_1"

@pytest.mark.asyncio
async def test_redis_memory_service_add(mock_redis: AsyncMock) -> None:
    service = RedisMemoryService(mock_redis)
    session = Session(app_name="test_app", user_id="user_1", id="sesh_1")
    event = Event(
        author="user",
        timestamp=1600000000.0,
        content=Content(parts=[Part(text="Hello Redis")])
    )
    session.events.append(event)
    
    await service.add_session_to_memory(session)
    mock_redis.lpush.assert_called_once()

@pytest.mark.asyncio
async def test_redis_memory_service_search(mock_redis: AsyncMock) -> None:
    service = RedisMemoryService(mock_redis)
    
    event = Event(
        author="user",
        timestamp=1600000000.0,
        content=Content(parts=[Part(text="Hello Redis")])
    )
    mock_redis.lrange.return_value = [event.model_dump_json()]
    
    response = await service.search_memory(app_name="test_app", user_id="user_1", query="redis")
    assert len(response.memories) == 1
    assert response.memories[0].author == "user"
