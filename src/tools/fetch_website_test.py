"""
src/tools/fetch_website_test.py
──────────────────────────────
Tests for the fetch_website tool including SSRF protections.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, AsyncMock
import httpx
import respx
from unittest.mock import patch

from src.tools.fetch_website import fetch_website

@pytest.mark.asyncio
async def test_fetch_website_invalid_scheme() -> None:
    result = await fetch_website.ainvoke({"url": "file:///etc/passwd"})
    assert "Only http/https URLs are permitted" in result


@pytest.mark.asyncio
async def test_fetch_website_ssrf_blocked_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    monkeypatch.setattr(socket, "gethostbyname", lambda _: "127.0.0.1")
    result = await fetch_website.ainvoke({"url": "http://localhost:8080/admin"})
    assert "SSRF protection blocked this URL" in result


@pytest.mark.asyncio
@respx.mock
async def test_fetch_website_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    monkeypatch.setattr(socket, "gethostbyname", lambda _: "8.8.8.8")
    respx.get("https://example.com").mock(return_value=httpx.Response(200, text="<html><body><h1>Example Domain</h1></body></html>"))
    result = await fetch_website.ainvoke({"url": "https://example.com"})
    assert "Example Domain" in result
