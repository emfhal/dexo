"""
src/context/budget.py
────────────────────────
Token budget manager — tracks per-section token counts
to replicate the context-window visualizer (purple/green/orange/pink bar).

Sections mirror the UI exactly:
  System prompt | Tool definitions | Rules | Skills | MCP | Subagents | Summary | Conversation
"""

from __future__ import annotations

import tiktoken

from src.graph.state import ContextBudget

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Fast token count using tiktoken (cl100k_base covers GPT-4 / Claude)."""
    return len(_ENCODING.encode(text, disallowed_special=()))


class BudgetManager:
    """
    Accumulates token counts per section and enforces the total budget.
    Returns a ContextBudget Pydantic model that can be stored in AgentState.

    Usage:
        bm = BudgetManager(budget_limit=16000)
        bm.add("system_prompt", system_prompt_text)
        bm.add("rules", rules_text)
        budget = bm.build()
        if budget.is_over_budget:
            # trim the most expensive section
    """

    _SECTION_FIELDS = [
        "system_prompt",
        "tool_definitions",
        "rules",
        "skills",
        "mcp",
        "subagents",
        "summary",
        "conversation",
    ]

    def __init__(self, budget_limit: int = 16_000) -> None:
        self._limit = budget_limit
        self._counts: dict[str, int] = {s: 0 for s in self._SECTION_FIELDS}

    def add(self, section: str, text: str) -> int:
        """Count tokens for a section and accumulate. Returns tokens added."""
        if section not in self._counts:
            raise ValueError(f"Unknown section '{section}'. Valid: {self._SECTION_FIELDS}")
        n = count_tokens(text)
        self._counts[section] += n
        return n

    def remaining(self) -> int:
        return self._limit - sum(self._counts.values())

    def build(self) -> ContextBudget:
        total = sum(self._counts.values())
        return ContextBudget(
            total_tokens=total,
            budget_limit=self._limit,
            system_prompt_tokens=self._counts["system_prompt"],
            tool_definitions_tokens=self._counts["tool_definitions"],
            rules_tokens=self._counts["rules"],
            skills_tokens=self._counts["skills"],
            mcp_tokens=self._counts["mcp"],
            subagent_tokens=self._counts["subagents"],
            summary_tokens=self._counts["summary"],
            conversation_tokens=self._counts["conversation"],
        )
