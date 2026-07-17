"""
src/memory/backends/mem0.py
──────────────────────────────
Mem0 adapter: persistent user-level facts and preferences.
Uses mem0's async client for non-blocking retrieval.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mem0 import AsyncMemoryClient  # type: ignore[import-untyped]

from src.observability.instrumentation import traced_memory

if TYPE_CHECKING:
    from src.config import MemoryConfig

logger = logging.getLogger(__name__)


class Mem0MemoryBackend:
    """
    Wraps the Mem0 async client.
    Mem0 stores user-level facts (preferences, identity, decisions)
    that persist across sessions — unlike Zep which is session-scoped.
    """

    def __init__(self, cfg: MemoryConfig) -> None:
        api_key = cfg.mem0_api_key.strip() if cfg.mem0_api_key else ""
        if api_key:
            self._client = AsyncMemoryClient(api_key=api_key)
        else:
            self._client = None

    # ── Write ────────────────────────────────────────────────────────────────
    async def add(
        self,
        messages: list[dict[str, str]],
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Ingest a conversation turn into Mem0.
        Messages format: [{"role": "user", "content": "..."}, ...]
        """
        if not self._client:
            return
        await self._client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata or {},
        )
        logger.debug("Mem0 add: %d messages for user %s", len(messages), user_id)

    # ── Read ─────────────────────────────────────────────────────────────────
    @traced_memory("mem0")
    async def search(
        self,
        query: str,
        user_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return top-k user facts most relevant to the query."""
        if not self._client:
            return []
        results = await self._client.search(query=query, user_id=user_id, limit=limit)
        logger.debug("Mem0 search '%s' → %d results for %s", query[:40], len(results), user_id)
        return results  # type: ignore[no-any-return]

    async def get_all(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieve all stored facts for a user."""
        if not self._client:
            return []
        return await self._client.get_all(user_id=user_id)  # type: ignore[no-any-return]

    async def delete_all(self, user_id: str) -> None:
        """GDPR-style: delete all memories for a user."""
        if not self._client:
            return
        await self._client.delete_all(user_id=user_id)
        logger.info("Deleted all Mem0 memories for user %s", user_id)
