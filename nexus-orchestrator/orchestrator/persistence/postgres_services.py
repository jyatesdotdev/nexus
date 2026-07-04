import logging
import os
from datetime import datetime
from typing import Any, List

from sqlalchemy import String, JSON, DateTime, select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector # type: ignore
from google import genai # type: ignore

from typing_extensions import override
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from google.adk.sessions.session import Session

logger = logging.getLogger(__name__)

def get_genai_client() -> genai.Client:
    """Lazily initializes the GenAI client."""
    # EDUCATIONAL NOTE: We use the same API key as the main orchestrator for embeddings.
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # During testing or if key is missing, we might not want to crash immediately
        # if embeddings aren't strictly required for the current operation.
        logger.warning("GEMINI_API_KEY or GOOGLE_API_KEY not found. Embeddings will fail.")
    return genai.Client(api_key=api_key)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class DBMemoryEntry(Base):
    __tablename__ = "memory_entries"
    id: Mapped[int] = mapped_column(primary_key=True)
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    author: Mapped[str | None] = mapped_column(String(100))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    # EDUCATIONAL NOTE: pgvector Integration
    # We store the semantic vector here. 768 is the default dimension for 
    # Gemini's 'text-embedding-004' model.
    embedding: Mapped[Any] = mapped_column(Vector(768), nullable=True)

class PostgresMemoryService(BaseMemoryService):
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            async with self.engine.begin() as conn:
                # EDUCATIONAL NOTE: PostgreSQL Vector Extension
                # We must ensure the 'vector' extension is enabled in the database
                # before we can use the Vector column type or distance operators.
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.run_sync(Base.metadata.create_all)
            self._initialized = True

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generates a 768-dimensional embedding using Gemini."""
        # EDUCATIONAL NOTE: Text Embeddings
        # This converts human language into a fixed-length numerical array.
        # Similar meanings will result in vectors that are geometrically 'close'
        # in the high-dimensional space.
        if not text.strip():
            return []
            
        try:
            client = get_genai_client()
            response = client.models.embed_content(
                model='text-embedding-004',
                contents=text
            )
            # Embeddings are returned as a list of embedding objects, each with 'values'
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return []

    @override
    async def add_session_to_memory(self, session: Session) -> None:
        await self._ensure_initialized()
        async with self.session_factory() as db_session:
            for event in session.events:
                if event.content and event.content.parts:
                    # Combine all text parts for embedding generation
                    full_text = " ".join([p.text for p in event.content.parts if p.text])
                    embedding = await self._generate_embedding(full_text) if full_text else None
                    
                    db_entry = DBMemoryEntry(
                        app_name=session.app_name,
                        user_id=session.user_id,
                        content=event.content.model_dump(),
                        author=event.author,
                        timestamp=datetime.fromtimestamp(event.timestamp),
                        embedding=embedding
                    )
                    db_session.add(db_entry)
            await db_session.commit()

    @override
    async def search_memory(
        self, *, app_name: str, user_id: str, query: str
    ) -> SearchMemoryResponse:
        await self._ensure_initialized()
        
        # EDUCATIONAL NOTE: RAG (Retrieval-Augmented Generation)
        # To search by meaning, we first embed the user's query string into a vector.
        query_embedding = await self._generate_embedding(query)
        
        async with self.session_factory() as db_session:
            if query_embedding:
                # EDUCATIONAL NOTE: Cosine Distance
                # We use the <=> operator (cosine distance) to find the most semantically
                # relevant memories. Lower distance means higher similarity.
                stmt = select(DBMemoryEntry).where(
                    DBMemoryEntry.app_name == app_name,
                    DBMemoryEntry.user_id == user_id
                ).order_by(
                    DBMemoryEntry.embedding.cosine_distance(query_embedding)
                ).limit(5)
            else:
                # Fallback to standard chronological search if embeddings fail
                stmt = select(DBMemoryEntry).where(
                    DBMemoryEntry.app_name == app_name,
                    DBMemoryEntry.user_id == user_id
                ).order_by(DBMemoryEntry.timestamp.desc()).limit(5)
            
            result = await db_session.execute(stmt)
            db_entries = result.scalars().all()
            
            response = SearchMemoryResponse()
            for entry in db_entries:
                response.memories.append(
                    MemoryEntry(
                        content=entry.content, # type: ignore
                        author=entry.author,
                        timestamp=entry.timestamp.isoformat()
                    )
                )
            return response
