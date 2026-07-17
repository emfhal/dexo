"""
src/context/sources/mcp_tools.py
────────────────────────────────────
MCP (Model Context Protocol) client adapter.
Reads a JSON config file listing MCP servers, connects to each,
and discovers available tools at runtime.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPToolDiscovery:
    """
    Connects to each configured MCP server and aggregates their tool schemas.

    mcp_servers.json format:
    [
      {
        "name": "filesystem",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
      },
      {
        "name": "supabase",
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server-supabase@latest", "--access-token", "..."]
      }
    ]
    """

    def __init__(self, config_path: str) -> None:
        self._config_path = Path(config_path)
        self._tools: list[dict[str, Any]] = []

    async def discover(self) -> list[dict[str, Any]]:
        """Load all tools from all configured MCP servers."""
        if not self._config_path.exists():
            logger.warning("MCP config not found: %s", self._config_path)
            return []

        servers: list[dict[str, Any]] = json.loads(self._config_path.read_text())
        results = await asyncio.gather(
            *[self._discover_server(s) for s in servers],
            return_exceptions=True,
        )

        all_tools: list[dict[str, Any]] = []
        for server, result in zip(servers, results, strict=False):
            if isinstance(result, Exception):
                logger.error("MCP server '%s' discovery failed: %s", server["name"], result)
            else:
                all_tools.extend(result)  # type: ignore[arg-type]

        logger.info("Discovered %d tools across %d MCP servers.", len(all_tools), len(servers))
        self._tools = all_tools
        return all_tools

    async def _discover_server(self, server: dict[str, Any]) -> list[dict[str, Any]]:
        params = StdioServerParameters(
            command=server["command"],
            args=server.get("args", []),
            env=server.get("env"),
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            return [
                {
                    "server": server["name"],
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                }
                for tool in tools_result.tools
            ]

    @property
    def tools(self) -> list[dict[str, Any]]:
        return self._tools
