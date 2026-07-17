"""
src/memory/backends/zep.py
─────────────────────────────
Zep adapter: long-term semantic memory, automatic entity extraction,
and conversation summarization via the Zep cloud/self-hosted API.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from zep_python.client import AsyncZep
from zep_python.types import Message, SessionSearchResult

from src.observability.instrumentation import traced_memory

if TYPE_CHECKING:
    from src.config import MemoryConfig

logger = logging.getLogger(__name__)


class ZepMemoryBackend:
    """
    Wraps zep-python's async client.
    - Manages sessions per LangGraph thread_id
    - Provides semantic search across long-term memory
    - Provides entity extraction results
    """

    def __init__(self, cfg: MemoryConfig) -> None:
        self._client = AsyncZep(
            base_url=str(cfg.zep_api_url),
            api_key=cfg.zep_api_key,
        )

    # ── Session management ───────────────────────────────────────────────────
    async def ensure_session(self, session_id: str, user_id: str) -> None:
        """Create a Zep session if it doesn't already exist."""
        try:
            await self._client.memory.get_session(session_id)
        except Exception:
            await self._client.memory.add_session(
                session_id=session_id,
                user_id=user_id,
                metadata={"created_by": "langgraph-src"},
            )
            logger.debug("Created Zep session %s for user %s", session_id, user_id)

    # ── Write ────────────────────────────────────────────────────────────────
    async def add_turn(
        self,
        session_id: str,
        human_message: str,
        ai_message: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        messages = [
            Message(role="human", content=human_message),
            Message(role="ai", content=ai_message),
        ]
        await self._client.memory.add_memory(session_id, messages=messages)

    # ── Read: Semantic Search ────────────────────────────────────────────────
    @traced_memory("zep")
    async def search(
        self,
        session_id: str,
        query: str,
        limit: int = 5,
    ) -> list[SessionSearchResult]:
        results = await self._client.memory.search_memory(
            session_id=session_id,
            text=query,
            limit=limit,
        )
        logger.debug("Zep search '%s' → %d results", query[:40], len(results))
        return results

    # ── Read: Summary ────────────────────────────────────────────────────────
    async def get_summary(self, session_id: str) -> str:
        memory = await self._client.memory.get_memory(session_id)
        return memory.summary.content if memory and memory.summary else ""

    # ── Read: Entity Context ─────────────────────────────────────────────────
    async def get_entity_context(self, session_id: str) -> list[dict[str, Any]]:
        memory = await self._client.memory.get_memory(session_id)
        if not memory or not memory.facts:
            return []
        return [{"fact": fact} for fact in memory.facts]
