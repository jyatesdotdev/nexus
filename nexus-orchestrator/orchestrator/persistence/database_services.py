import logging
from typing import Any, Optional, List
from sqlalchemy import String, JSON, select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from google.adk.sessions.session import Session
from google.adk.sessions.base_session_service import BaseSessionService, GetSessionConfig, ListSessionsResponse
from google.adk.events.event import Event
from google.adk.platform import uuid as platform_uuid
from google.adk.platform import time as platform_time
from typing_extensions import override

logger = logging.getLogger(__name__)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class DBSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    last_update_time: Mapped[float] = mapped_column(nullable=False)
    events: Mapped[List[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

class DatabaseSessionService(BaseSessionService):
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._initialized = True

    @override
    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: Optional[dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> Session:
        await self._ensure_initialized()
        session_id = session_id or platform_uuid.new_uuid()
        
        session = Session(
            app_name=app_name,
            user_id=user_id,
            id=session_id,
            state=state or {},
            last_update_time=platform_time.get_time(),
        )
        
        async with self.session_factory() as db_session:
            db_entry = DBSession(
                id=session_id,
                app_name=app_name,
                user_id=user_id,
                state=session.state,
                last_update_time=session.last_update_time,
                events=[e.model_dump() for e in session.events]
            )
            db_session.add(db_entry)
            await db_session.commit()
        
        return session

    @override
    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: Optional[GetSessionConfig] = None,
    ) -> Optional[Session]:
        await self._ensure_initialized()
        async with self.session_factory() as db_session:
            stmt = select(DBSession).where(
                DBSession.app_name == app_name,
                DBSession.user_id == user_id,
                DBSession.id == session_id
            )
            result = await db_session.execute(stmt)
            db_entry = result.scalar_one_or_none()
            
            if not db_entry:
                return None
            
            session = Session(
                app_name=db_entry.app_name,
                user_id=db_entry.user_id,
                id=db_entry.id,
                state=db_entry.state,
                last_update_time=db_entry.last_update_time,
                events=[Event.model_validate(e) for e in db_entry.events]
            )
            
            if config:
                if config.num_recent_events:
                    session.events = session.events[-config.num_recent_events:]
                if config.after_timestamp:
                    session.events = [e for e in session.events if e.timestamp >= config.after_timestamp]
            
            return session

    @override
    async def list_sessions(
        self, *, app_name: str, user_id: Optional[str] = None
    ) -> ListSessionsResponse:
        await self._ensure_initialized()
        async with self.session_factory() as db_session:
            stmt = select(DBSession).where(DBSession.app_name == app_name)
            if user_id:
                stmt = stmt.where(DBSession.user_id == user_id)
            
            result = await db_session.execute(stmt)
            db_entries = result.scalars().all()
            
            sessions = []
            for entry in db_entries:
                # list_sessions usually returns sessions without events for efficiency
                session = Session(
                    app_name=entry.app_name,
                    user_id=entry.user_id,
                    id=entry.id,
                    state=entry.state,
                    last_update_time=entry.last_update_time,
                    events=[]
                )
                sessions.append(session)
            
            return ListSessionsResponse(sessions=sessions)

    @override
    async def delete_session(
        self, *, app_name: str, user_id: str, session_id: str
    ) -> None:
        await self._ensure_initialized()
        async with self.session_factory() as db_session:
            stmt = delete(DBSession).where(
                DBSession.app_name == app_name,
                DBSession.user_id == user_id,
                DBSession.id == session_id
            )
            await db_session.execute(stmt)
            await db_session.commit()

    @override
    async def append_event(self, session: Session, event: Event) -> Event:
        if event.partial:
            return event
            
        await super().append_event(session=session, event=event)
        
        # Persist updated session
        await self._ensure_initialized()
        async with self.session_factory() as db_session:
            stmt = select(DBSession).where(
                DBSession.app_name == session.app_name,
                DBSession.user_id == session.user_id,
                DBSession.id == session.id
            )
            result = await db_session.execute(stmt)
            db_entry = result.scalar_one_or_none()
            
            if db_entry:
                db_entry.events = [e.model_dump() for e in session.events]
                db_entry.last_update_time = session.last_update_time
                await db_session.commit()
        
        return event
