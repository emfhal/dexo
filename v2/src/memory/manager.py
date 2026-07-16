"""
src/memory/manager.py
────────────────────────
Unified MemoryManager facade.
Abstracts Postgres (checkpointing), Zep (semantic/entity), and
Mem0 (user facts) behind a single async interface.

Callers only import MemoryManager — not individual backends.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config import DatabaseConfig, MemoryConfig
from src.memory.backends.mem0 import Mem0MemoryBackend
from src.memory.backends.postgres import PostgresMemoryBackend
from src.memory.backends.zep import ZepMemoryBackend
from src.memory.fusion import MemoryFusion

logger = logging.getLogger(__name__)


@dataclass
class RetrievedMemory:
    source: str          # "zep" | "mem0"
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryManager:
    """
    Single interface for all memory operations.

    Architecture:
    ┌──────────────────────────────────────────────┐
    │               MemoryManager                  │
    │  ┌──────────┐  ┌──────┐  ┌────────────────┐ │
    │  │ Postgres │  │  Zep │  │      Mem0      │ │
    │  │(checkpoint│  │(semantic│ │(user facts)    │ │
    │  │  / state)│  │entity)│  │                │ │
    │  └──────────┘  └──────┘  └────────────────┘ │
    └──────────────────────────────────────────────┘
    """

    def __init__(self, db_cfg: DatabaseConfig, mem_cfg: MemoryConfig) -> None:
        self.postgres = PostgresMemoryBackend(db_cfg)
        self.zep = ZepMemoryBackend(mem_cfg)
        self.mem0 = Mem0MemoryBackend(mem_cfg)
        self._fusion = MemoryFusion()

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    async def startup(self) -> None:
        await self.postgres.connect()
        logger.info("MemoryManager ready.")

    async def shutdown(self) -> None:
        await self.postgres.disconnect()

    # ── Retrieve: fan-out to Zep + Mem0 in parallel ───────────────────────────
    async def retrieve(
        self,
        query: str,
        user_id: str,
        session_id: str,
        zep_limit: int = 5,
        mem0_limit: int = 5,
    ) -> list[RetrievedMemory]:
        """
        Retrieves relevant memories from all backends concurrently
        and merges them with de-duplication and re-ranking.
        """
        try:
            await self.zep.ensure_session(session_id, user_id)
        except Exception as e:
            logger.warning(f"Failed to ensure zep session: {e}")

        zep_task = self.zep.search(session_id, query, limit=zep_limit)
        mem0_task = self.mem0.search(query, user_id, limit=mem0_limit)

        zep_results, mem0_results = await asyncio.gather(
            zep_task, mem0_task, return_exceptions=True
        )

        memories: list[RetrievedMemory] = []

        if not isinstance(zep_results, Exception):
            for r in zep_results:
                memories.append(
                    RetrievedMemory(
                        source="zep",
                        content=r.message.content if r.message else str(r),
                        score=r.score or 0.0,
                        metadata={"dist": r.dist},
                    )
                )
        else:
            logger.warning("Zep retrieval failed: %s", zep_results)

        if not isinstance(mem0_results, Exception):
            for r in mem0_results:
                memories.append(
                    RetrievedMemory(
                        source="mem0",
                        content=r.get("memory", ""),
                        score=r.get("score", 0.0),
                        metadata=r.get("metadata", {}),
                    )
                )
        else:
            logger.warning("Mem0 retrieval failed: %s", mem0_results)

        return self._fusion.merge(memories)

    # ── Store: persist a completed conversation turn ──────────────────────────
    async def store_turn(
        self,
        user_id: str,
        session_id: str,
        human_message: str,
        ai_message: str,
    ) -> None:
        """
        Persists a turn to Zep (for semantic indexing) and
        Mem0 (for user-fact extraction). Fire-and-forget via asyncio.gather.
        """
        await asyncio.gather(
            self.zep.add_turn(session_id, human_message, ai_message),
            self.mem0.add(
                messages=[
                    {"role": "user", "content": human_message},
                    {"role": "assistant", "content": ai_message},
                ],
                user_id=user_id,
            ),
            return_exceptions=True,  # Don't let storage failures crash the src
        )

    # ── Convenience: session summary for context injection ───────────────────
    async def get_conversation_summary(self, session_id: str) -> str:
        try:
            return await self.zep.get_summary(session_id)
        except Exception as e:
            logger.warning(f"Failed to get zep summary: {e}")
            return ""
