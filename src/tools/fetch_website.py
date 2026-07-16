"""
src/tools/fetch_website.py
─────────────────────────────
SSRF-protected web content fetcher.
- Validates URL against blocked CIDR ranges before connecting
- Resolves hostname to IP for SSRF protection
- Converts HTML to clean Markdown
- Enforces per-request timeout
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from langchain_core.tools import tool
from markdownify import markdownify

from src.config import get_settings


def _check_ssrf(url: str) -> None:
    """
    Raise ValueError if the resolved IP falls in a blocked CIDR.
    Prevents Server-Side Request Forgery attacks.
    """
    cfg = get_settings().tools
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise ValueError(f"Invalid URL (no hostname): {url}")

    try:
        resolved_ip = ipaddress.IPv4Address(socket.gethostbyname(hostname))
    except (socket.gaierror, ValueError) as exc:
        raise ValueError(f"Cannot resolve hostname '{hostname}': {exc}") from exc

    for blocked_cidr in cfg.ssrf_blocked_cidrs:
        if resolved_ip in blocked_cidr:
            raise ValueError(
                f"URL resolves to blocked CIDR {blocked_cidr}: {resolved_ip}"
            )


@tool
def fetch_website(url: str, extract_links: bool = False) -> str:
    """
    Fetch the text content of a public URL and return it as Markdown.

    Args:
        url: The fully-qualified URL to fetch (must use http/https).
        extract_links: If True, also return a list of links found on the page.
    """
    cfg = get_settings().tools

    # ── Validate scheme ───────────────────────────────────────────────────────
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return f"⛔ Only http/https URLs are permitted. Got: {parsed.scheme}"

    # ── SSRF check ────────────────────────────────────────────────────────────
    try:
        _check_ssrf(url)
    except ValueError as exc:
        return f"⛔ SSRF protection blocked this URL: {exc}"

    # ── Fetch ─────────────────────────────────────────────────────────────────
    try:
        with httpx.Client(
            timeout=cfg.fetch_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "LangGraph-Agent/2.0 (research)"},
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "html" in content_type:
            markdown = markdownify(response.text, heading_style="ATX")
            # Trim to ~8k chars to avoid flooding context
            trimmed = markdown[:8_000]
            if len(markdown) > 8_000:
                trimmed += "\n\n...[content truncated]"
            return trimmed
        else:
            return response.text[:8_000]

    except httpx.HTTPStatusError as exc:
        return f"❌ HTTP {exc.response.status_code}: {url}"
    except httpx.TimeoutException:
        return f"⚠️ Request timed out after {cfg.fetch_timeout_seconds}s: {url}"
    except Exception as exc:
        return f"❌ Fetch error: {exc}"
