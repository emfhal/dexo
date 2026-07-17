"""
src/memory/backends/postgres.py
──────────────────────────────────
Postgres-backed LangGraph checkpointer + message store.
Uses langgraph-checkpoint-postgres with connection pooling via psycopg3.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from src.config import DatabaseConfig

logger = logging.getLogger(__name__)


class PostgresMemoryBackend:
    """
    Manages the async connection pool and exposes the LangGraph
    AsyncPostgresSaver as a context manager.

    Usage:
        backend = PostgresMemoryBackend(cfg)
        async with backend.checkpointer() as saver:
            graph = workflow.compile(checkpointer=saver)
    """

    def __init__(self, cfg: DatabaseConfig) -> None:
        self._dsn = str(cfg.url)
        self._pool_size = cfg.pool_size
        self._max_overflow = cfg.max_overflow
        self._pool: AsyncConnectionPool | None = None

    async def connect(self) -> None:
        """Open the pool. Call during application lifespan startup."""
        self._pool = AsyncConnectionPool(
            conninfo=self._dsn,
            min_size=2,
            max_size=self._pool_size + self._max_overflow,
            open=False,
        )
        await self._pool.open()
        logger.info("Postgres pool open (max_size=%d)", self._pool_size + self._max_overflow)

    async def disconnect(self) -> None:
        """Close the pool. Call during application lifespan shutdown."""
        if self._pool:
            await self._pool.close()
            logger.info("Postgres pool closed.")

    @asynccontextmanager
    async def checkpointer(self) -> AsyncIterator[AsyncPostgresSaver]:
        """
        Yields an AsyncPostgresSaver scoped to a single request/conversation.
        Runs DDL migrations the first time (idempotent).
        """
        if not self._pool:
            raise RuntimeError("PostgresMemoryBackend.connect() must be called first.")

        async with await psycopg.AsyncConnection.connect(self._dsn, autocommit=True) as conn:
            saver = AsyncPostgresSaver(conn)
            await saver.setup()  # Idempotent DDL migrations
            yield saver
