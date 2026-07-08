import logging
from typing import Any, Optional, cast

from redis.asyncio import Redis
from google.adk.sessions.session import Session
from google.adk.sessions.base_session_service import BaseSessionService, GetSessionConfig, ListSessionsResponse
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.events.event import Event
from google.adk.platform import uuid as platform_uuid
from google.adk.platform import time as platform_time
from typing_extensions import override

logger = logging.getLogger(__name__)

# EDUCATIONAL NOTE: Whole-Session Blobs and a Manual Index
# Redis is a key-value store — it cannot answer "which sessions does this user
# have?" without help, so we maintain a secondary SET (sessions_list:*) as a
# hand-rolled index and must keep it in sync on create/delete ourselves. The
# session itself is stored as ONE Pydantic-JSON blob rewritten on every
# append_event: each write is O(session length), but a single SET is atomic,
# so readers never observe a half-updated session (appending to a separate
# Redis LIST would be cheaper per event but splits one logical object across
# keys with no transaction tying them together). The memory service below
# shows the low-tech end of the retrieval spectrum — naive keyword matching
# over a full LRANGE scan — as a contrast to the pgvector backend's semantic
# search.
class RedisSessionService(BaseSessionService):
    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def _get_session_key(self, app_name: str, user_id: str, session_id: str) -> str:
        return f"session:{app_name}:{user_id}:{session_id}"

    def _get_sessions_list_key(self, app_name: str, user_id: str) -> str:
        return f"sessions_list:{app_name}:{user_id}"

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        session_id = session_id or platform_uuid.new_uuid()
        key = self._get_session_key(app_name, user_id, session_id)
        
        if await self._redis.exists(key):
             # ADK's InMemorySessionService raises AlreadyExistsError if session_id is provided and exists
             pass

        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
            last_update_time=platform_time.get_time(),
        )
        
        await self._redis.set(key, session.model_dump_json())
        await self._redis.sadd(self._get_sessions_list_key(app_name, user_id), session_id)
        
        return session

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        key = self._get_session_key(app_name, user_id, session_id)
        data = await self._redis.get(key)
        if not data:
            return None
        
        # Cast to str because redis.asyncio returns Any but we expect str|bytes
        session = Session.model_validate_json(cast(str, data))
        
        if config:
            if config.num_recent_events:
                session.events = session.events[-config.num_recent_events:]
            if config.after_timestamp:
                session.events = [e for e in session.events if e.timestamp >= config.after_timestamp]
        
        return session

    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        sessions = []
        if user_id:
            session_ids = await self._redis.smembers(self._get_sessions_list_key(app_name, user_id))
            for sid in session_ids:
                sid_str = sid.decode('utf-8') if isinstance(sid, bytes) else cast(str, sid)
                session = await self.get_session(app_name=app_name, user_id=user_id, session_id=sid_str)
                if session:
                    # list_sessions usually returns sessions without events for efficiency
                    session.events = []
                    sessions.append(session)
        else:
            # Listing all sessions for all users might be expensive in Redis if not indexed properly
            pass
            
        return ListSessionsResponse(sessions=sessions)

    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        key = self._get_session_key(app_name, user_id, session_id)
        await self._redis.delete(key)
        await self._redis.srem(self._get_sessions_list_key(app_name, user_id), session_id)

    async def append_event(self, session: Session, event: Event) -> Event:
        if event.partial:
            return event
            
        await super().append_event(session=session, event=event)
        
        # Persist updated session
        key = self._get_session_key(session.app_name, session.user_id, session.id)
        await self._redis.set(key, session.model_dump_json())
        
        return event

class RedisMemoryService(BaseMemoryService):
    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def _get_memory_key(self, app_name: str, user_id: str) -> str:
        return f"memory:{app_name}:{user_id}"

    @override
    async def add_session_to_memory(self, session: Session) -> None:
        key = self._get_memory_key(session.app_name, session.user_id)
        for event in session.events:
            if event.content and event.content.parts:
                await self._redis.lpush(key, event.model_dump_json())

    @override
    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        key = self._get_memory_key(app_name, user_id)
        data_list = await self._redis.lrange(key, 0, -1)
        
        words_in_query = set(word.lower() for word in query.split())
        response = SearchMemoryResponse()
        
        for data in data_list:
            event = Event.model_validate_json(cast(str, data))
            if not event.content or not event.content.parts:
                continue
            
            text = " ".join([part.text for part in event.content.parts if part.text]).lower()
            if any(word in text for word in words_in_query):
                response.memories.append(
                    MemoryEntry(
                        content=event.content,
                        author=event.author,
                        timestamp=str(event.timestamp),
                    )
                )
        
        return response
