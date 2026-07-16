"""
src/graph/nodes/llm.py
─────────────────────────
LLM reasoning node.
- Uses ProviderRegistry for multi-provider routing (Ollama/Gemini/OpenAI/Anthropic)
- Injects full context (rules, skills, memories, summary) into system message
- Handles fallback on rate-limit / connection errors with tenacity retry
- Emits OTEL metrics for token usage and latency
"""
from __future__ import annotations

import logging
import time
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.graph.state import AgentState
from src.observability.instrumentation import traced_node
from src.observability.metrics import (
    llm_latency_histogram,
    llm_requests_total,
    llm_tokens_total,
)
from src.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

# Provider registry is built once from config
_registry: ProviderRegistry | None = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry.from_config(get_settings().llm)
    return _registry


def _build_system_message(state: AgentState) -> SystemMessage:
    """Compose the full system message from loaded context + retrieved memories."""
    ctx = state.context
    parts: list[str] = [ctx.system_prompt]

    if ctx.rules:
        parts.append(f"\n## Rules\n{ctx.rules}")

    if ctx.skills:
        skills_text = "\n\n".join(
            f"### Skill: {name}\n{body}" for name, body in ctx.skills.items()
        )
        parts.append(f"\n## Skills\n{skills_text}")

    if ctx.conversation_summary:
        parts.append(f"\n## Previous Conversation Summary\n{ctx.conversation_summary}")

    if state.retrieved_memories:
        mem_text = "\n".join(
            f"- [{m['source']}] {m['content']}" for m in state.retrieved_memories
        )
        parts.append(f"\n## Relevant Memories\n{mem_text}")

    if ctx.mcp_tools:
        tool_names = ", ".join(t.get("name", "?") for t in ctx.mcp_tools)
        parts.append(f"\n## Available MCP Tools\n{tool_names}")

    if ctx.subagent_definitions:
        subs = "\n".join(
            f"- **{s['name']}**: {s['description']}" for s in ctx.subagent_definitions
        )
        parts.append(f"\n## Available Subagents\n{subs}")

    return SystemMessage(content="\n".join(parts))


@traced_node("llm")
async def llm_node(state: AgentState, tools: list[Any]) -> dict[str, Any]:
    """
    LangGraph node — LLM reasoning step.
    Returns updated messages with the AI response appended.
    """
    registry = get_registry()
    system_msg = _build_system_message(state)
    messages = [system_msg, *state.messages]

    primary_llm = registry.build_primary()
    llm_with_tools = primary_llm.bind_tools(tools)

    provider_info = registry.primary_info
    t0 = time.perf_counter()

    try:
        response = await _invoke_with_fallback(llm_with_tools, messages, registry)
    except Exception as exc:
        logger.exception("LLM call failed after all retries.")
        raise

    latency_ms = (time.perf_counter() - t0) * 1000

    # ── OTEL Metrics ──────────────────────────────────────────────────────────
    llm_requests_total.add(1, {"provider": provider_info["provider"], "model": provider_info["model"]})
    llm_latency_histogram.record(round(latency_ms, 2), {"provider": provider_info["provider"]})

    if hasattr(response, "usage_metadata") and response.usage_metadata:
        total = (
            response.usage_metadata.get("input_tokens", 0)
            + response.usage_metadata.get("output_tokens", 0)
        )
        llm_tokens_total.add(total, {"provider": provider_info["provider"]})

    return {"messages": [response], "iteration": state.iteration + 1}


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _invoke_with_fallback(
    primary_llm: Any,
    messages: list[Any],
    registry: ProviderRegistry,
) -> AIMessage:
    """
    Attempts the primary LLM with exponential backoff.
    On rate-limit or connection error, switches to fallback provider.
    """
    try:
        return await primary_llm.ainvoke(messages)
    except Exception as exc:
        exc_str = str(exc).lower()
        is_retriable = any(
            keyword in exc_str
            for keyword in ("rate_limit", "rate limit", "529", "503", "connection", "timeout")
        )
        if is_retriable:
            logger.warning(
                "Primary LLM error (%s) — switching to fallback provider.", type(exc).__name__
            )
            fallback = registry.build_fallback()
            return await fallback.ainvoke(messages)
        raise
