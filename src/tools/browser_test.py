"""
src/tools/browser_test.py
─────────────────────────
Tests for the browser tool.
"""
from __future__ import annotations

import json
import pytest

from src.tools.browser import browser_action

@pytest.mark.asyncio
async def test_browser_action_basic() -> None:
    actions = [
        {"action": "goto", "url": "https://example.com"},
        {"action": "extract_text", "selector": "h1"}
    ]
    result = await browser_action.ainvoke({"actions_json": json.dumps(actions)})
    
    assert "Example Domain" in result
    assert "Text from 'h1'" in result

@pytest.mark.asyncio
async def test_browser_action_invalid_json() -> None:
    result = await browser_action.ainvoke({"actions_json": "invalid json"})
    assert "JSON Decode Error" in result

@pytest.mark.asyncio
async def test_browser_action_invalid_url() -> None:
    actions = [{"action": "goto", "url": "file:///etc/passwd"}]
    result = await browser_action.ainvoke({"actions_json": json.dumps(actions)})
    assert "Only http/https URLs are permitted" in result
