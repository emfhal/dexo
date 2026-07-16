"""
src/memory/memory_test.py
────────────────────────
Tests for memory components.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from src.config import DatabaseConfig, MemoryConfig
from src.memory.manager import MemoryManager

@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch) -> MemoryManager:
    db_cfg = DatabaseConfig()
    mem_cfg = MemoryConfig()
    
    with patch("src.memory.backends.mem0.AsyncMemoryClient"):
        with patch("src.memory.backends.zep.AsyncZep"):
            mgr = MemoryManager(db_cfg, mem_cfg)
            mgr.postgres = AsyncMock()
            mgr.zep = AsyncMock()
            mgr.mem0 = AsyncMock()
            return mgr

@pytest.mark.asyncio
async def test_memory_manager_retrieve(manager: MemoryManager) -> None:
    # Setup mocks
    manager.zep.search.return_value = []
    manager.zep.get_entity_context.return_value = []
    manager.mem0.search.return_value = []

    result = await manager.retrieve("Hello", "user123", "test_session")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_memory_manager_store_turn(manager: MemoryManager) -> None:
    await manager.store_turn("user123", "test_session", "Human", "AI")
    
    manager.zep.add_turn.assert_called_once()
    manager.mem0.add.assert_called_once()
