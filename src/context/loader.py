"""
src/context/loader.py
────────────────────────
AdvancedContextLoader — LangGraph node that assembles the full context window
before the LLM reasons. Mirrors the 8-section bar in the Antigravity UI:

  ① System prompt  ② Tool definitions  ③ Rules   ④ Skills
  ⑤ MCP & dynamic ⑥ Subagent defs     ⑦ Summary ⑧ Conversation

Sources:
  - System prompt  → src/assets/prompts/system_prompt.j2  (Jinja2)
  - Rules          → src/assets/rules/AGENTS.md            (with !include)
  - Skills         → src/assets/skills/**/SKILL.md
  - Subagents      → src/assets/subagents/**/manifest.json + SKILL.md
  - MCP tools      → src/assets/mcp/servers.json
  - Summary        → Zep conversation summary
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from src.context.budget import BudgetManager
from src.context.sources.mcp_tools import MCPToolDiscovery
from src.context.sources.rules import load_rules
from src.context.sources.skills import load_skills
from src.graph.state import AgentState, LoadedContext
from src.observability.instrumentation import traced_node
from src.observability.metrics import context_tokens_histogram

if TYPE_CHECKING:
    from src.config import AssetsConfig
    from src.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


def _load_subagent_manifests(subagents_dir: str) -> list[dict[str, Any]]:
    """
    Discover all subagent manifests under src/assets/subagents/.
    Each subagent directory must have a manifest.json.
    Optionally includes its SKILL.md body.
    """
    root = Path(subagents_dir)
    if not root.exists():
        logger.warning("Subagents directory not found: %s", subagents_dir)
        return []

    manifests: list[dict[str, Any]] = []
    for manifest_file in root.rglob("manifest.json"):
        try:
            data = json.loads(manifest_file.read_text())
            skill_file = manifest_file.parent / "SKILL.md"
            if skill_file.exists():
                data["skill_body"] = skill_file.read_text()
            manifests.append(data)
        except Exception as exc:
            logger.error("Failed to load subagent manifest %s: %s", manifest_file, exc)

    logger.debug("Loaded %d subagent manifests from %s", len(manifests), subagents_dir)
    return manifests


class AdvancedContextLoader:
    """
    Async LangGraph node that assembles all context sections concurrently,
    enforces the token budget, and writes a LoadedContext into AgentState.
    """

    def __init__(self, cfg: AssetsConfig, memory: MemoryManager) -> None:
        self._cfg = cfg
        self._memory = memory
        self._mcp = MCPToolDiscovery(cfg.mcp_servers_config)

        # Jinja2 env pointing at src/assets/prompts/
        self._jinja_env = Environment(
            loader=FileSystemLoader(cfg.prompts_dir),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Warm caches (populated by warm_up())
        self._rules_cache: str | None = None
        self._skills_cache: list | None = None  # type: ignore[type-arg]
        self._subagents_cache: list[dict[str, Any]] | None = None

    # ── Warm-up ───────────────────────────────────────────────────────────────
    async def warm_up(self) -> None:
        """Pre-load all static context. Call once during application startup."""
        self._rules_cache = load_rules(self._cfg.rules_file)
        self._skills_cache = load_skills(self._cfg.skills_dir)
        self._subagents_cache = _load_subagent_manifests(self._cfg.subagents_dir)
        await self._mcp.discover()

        logger.info(
            "ContextLoader warm-up ✓ | skills=%d | subagents=%d | mcp_tools=%d",
            len(self._skills_cache),
            len(self._subagents_cache),
            len(self._mcp.tools),
        )

    # ── Main LangGraph node ───────────────────────────────────────────────────
    @traced_node("context_loader")
    async def __call__(self, state: AgentState) -> dict[str, Any]:
        """
        Assembles all context sections. Returns partial state update dict.
        """
        auth = state.auth
        if not auth:
            logger.error("ContextLoader invoked without AuthContext — skipping.")
            return {}

        budget = BudgetManager(budget_limit=self._cfg.context_token_budget)

        # ── Fetch dynamic data concurrently ───────────────────────────────────
        summary = await self._memory.get_conversation_summary(auth.session_id)

        # ── ① System prompt ───────────────────────────────────────────────────
        memories_for_prompt = [
            {"source": m["source"], "content": m["content"]}
            for m in state.retrieved_memories[:5]  # Top 5 most relevant
        ]
        system_prompt = self._render_prompt(
            user_id=auth.user_id,
            roles=[p.role for p in auth.permissions],
            memories=memories_for_prompt,
            conversation_summary=summary,
            environment=state.context.budget.budget_limit > 0 and "production" or "development",
        )
        budget.add("system_prompt", system_prompt)

        # ── ② Rules ───────────────────────────────────────────────────────────
        rules = self._rules_cache or load_rules(self._cfg.rules_file)
        budget.add("rules", rules)

        # ── ③ Skills (budget-aware injection) ────────────────────────────────
        raw_skills = self._skills_cache or load_skills(self._cfg.skills_dir)
        injected_skills: dict[str, str] = {}
        for skill in raw_skills:
            tokens_needed = (
                budget.add("skills", skill["body"]) if budget.remaining() > 400 else None
            )
            if tokens_needed is not None:
                injected_skills[skill["name"]] = skill["body"]
            else:
                logger.debug("Token budget full — skipping skill '%s'.", skill["name"])
                break

        # ── ④ MCP tools ───────────────────────────────────────────────────────
        mcp_tools = self._mcp.tools
        if mcp_tools and budget.remaining() > 200:
            budget.add("mcp", json.dumps(mcp_tools))

        # ── ⑤ Subagent definitions ────────────────────────────────────────────
        subagents = self._subagents_cache or _load_subagent_manifests(self._cfg.subagents_dir)
        # Summarise for context (don't inject full skill bodies to save tokens)
        subagent_summaries = [
            {"name": s["name"], "description": s.get("description", "")} for s in subagents
        ]
        if subagent_summaries and budget.remaining() > 200:
            budget.add("subagents", json.dumps(subagent_summaries))

        # ── ⑥ Conversation summary (already injected via system prompt) ───────
        budget.add("summary", summary)

        # ── Build budget model ────────────────────────────────────────────────
        ctx_budget = budget.build()

        context_tokens_histogram.record(
            ctx_budget.total_tokens,
            {"user_id": auth.user_id},
        )

        if ctx_budget.is_over_budget:
            logger.warning(
                "Context OVER budget: %d/%d tokens (%.1f%%)",
                ctx_budget.total_tokens,
                ctx_budget.budget_limit,
                ctx_budget.used_pct,
            )
        else:
            logger.info(
                "Context assembled: %d tokens (%.1f%% of %d)",
                ctx_budget.total_tokens,
                ctx_budget.used_pct,
                ctx_budget.budget_limit,
            )

        return {
            "context": LoadedContext(
                system_prompt=system_prompt,
                rules=rules,
                skills=injected_skills,
                mcp_tools=mcp_tools,
                subagent_definitions=subagent_summaries,
                conversation_summary=summary,
                budget=ctx_budget,
            )
        }

    def _render_prompt(self, **kwargs: Any) -> str:
        """Render system_prompt.j2 from src/assets/prompts/."""
        from datetime import UTC, datetime

        try:
            template = self._jinja_env.get_template("system_prompt.j2")
            return template.render(
                now_utc=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                **kwargs,
            )
        except Exception as exc:
            logger.error("Failed to render system prompt template: %s", exc)
            return f"You are a helpful AI assistant. User: {kwargs.get('user_id', 'unknown')}"

    @staticmethod
    def _last_user_message(state: AgentState) -> str:
        for msg in reversed(state.messages):
            if hasattr(msg, "type") and msg.type == "human":
                return str(msg.content)
        return ""
