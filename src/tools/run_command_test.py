"""
src/tools/run_command_test.py
────────────────────────────
Tests for the run_command tool.
"""
from __future__ import annotations

import pytest

from src.tools.run_command import run_command

@pytest.mark.asyncio
async def test_run_command_not_allowed() -> None:
    # 'rm' is not in the default allowlist
    result = await run_command.ainvoke({"command": "rm -rf /"})
    assert "Command 'rm' is not in the allowlist" in result

@pytest.mark.asyncio
async def test_run_command_allowed() -> None:
    # 'echo' is in the allowlist
    result = await run_command.ainvoke({"command": "echo 'hello'"})
    assert "hello" in result
