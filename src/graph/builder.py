"""
src/graph/builder.py
───────────────────────
Compiles the LangGraph StateGraph with all nodes, edges,
conditional routing, and the Postgres checkpointer.

Graph topology:
  [START] → auth → memory_retrieve → context_loader → generate → tools → generate → ...
                                                           ↘ [END] (no tool calls)
"""

from __future__ import annotations

import functools
import logging
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.graph.nodes.auth import auth_node
from src.graph.nodes.llm import llm_node
from src.graph.state import AgentState
from src.tools.ask_followup import ask_followup
from src.tools.browser import browser_action
from src.tools.fetch_website import fetch_website
from src.tools.read_skill import read_skill
from src.tools.run_command import run_command

if TYPE_CHECKING:
    from src.context.loader import AdvancedContextLoader
    from src.memory.manager import MemoryManager

logger = logging.getLogger(__name__)

# ── All tools available to the src ─────────────────────────────────────────
AGENT_TOOLS = [fetch_website, run_command, read_skill, ask_followup, browser_action]


def _should_continue(state: AgentState) -> Literal["tools", "end"]:
    """
    Conditional edge: check if the last message contains tool calls.
    Also enforces the max iteration guard.
    """
    if state.iteration >= state.max_iterations:
        logger.warning("Max iterations (%d) reached.", state.max_iterations)
        return "end"

    last_message = state.messages[-1] if state.messages else None
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"


async def _memory_retrieve_node(state: AgentState, memory: MemoryManager) -> dict[str, Any]:
    """Node: retrieves relevant memories before LLM reasoning."""
    if not state.auth or not state.messages:
        return {}

    # Extract the latest user query for retrieval
    last_human = next(
        (m.content for m in reversed(state.messages) if hasattr(m, "type") and m.type == "human"),
        "",
    )
    if not last_human:
        return {}

    memories = await memory.retrieve(
        query=last_human,
        user_id=state.auth.user_id,
        session_id=state.auth.session_id,
    )
    return {
        "retrieved_memories": [
            {"source": m.source, "content": m.content, "score": m.score} for m in memories
        ]
    }


async def _memory_store_node(state: AgentState, memory: MemoryManager) -> dict[str, Any]:
    """Node: persists the completed turn to Zep + Mem0 after LLM response."""
    if not state.auth or len(state.messages) < 2:
        return {}

    # Find last human + AI message pair
    last_ai = next((m for m in reversed(state.messages) if isinstance(m, AIMessage)), None)
    last_human = next(
        (m.content for m in reversed(state.messages) if hasattr(m, "type") and m.type == "human"),
        None,
    )

    if last_ai and last_human:
        await memory.store_turn(
            user_id=state.auth.user_id,
            session_id=state.auth.session_id,
            human_message=last_human,
            ai_message=last_ai.content
            if isinstance(last_ai.content, str)
            else str(last_ai.content),
        )
    return {}


def build_graph(memory: MemoryManager, context_loader: AdvancedContextLoader) -> Any:
    """
    Constructs and compiles the full LangGraph StateGraph.
    Returns a compiled graph ready for invocation.
    """
    workflow = StateGraph(AgentState)

    # ── Bind dependencies to nodes ────────────────────────────────────────────
    memory_retrieve = functools.partial(_memory_retrieve_node, memory=memory)
    memory_store = functools.partial(_memory_store_node, memory=memory)
    generate = functools.partial(llm_node, tools=AGENT_TOOLS)
    tool_node = ToolNode(AGENT_TOOLS)

    # ── Register nodes ────────────────────────────────────────────────────────
    workflow.add_node("auth", auth_node)
    workflow.add_node("memory_retrieve", memory_retrieve)
    workflow.add_node("context_loader", context_loader)
    workflow.add_node("generate", generate)
    workflow.add_node("tools", tool_node)
    workflow.add_node("memory_store", memory_store)

    # ── Edges ─────────────────────────────────────────────────────────────────
    workflow.add_edge(START, "auth")
    workflow.add_edge("auth", "memory_retrieve")
    workflow.add_edge("memory_retrieve", "context_loader")
    workflow.add_edge("context_loader", "generate")

    # Conditional: Generate → tools or END
    workflow.add_conditional_edges(
        "generate",
        _should_continue,
        {"tools": "tools", "end": "memory_store"},
    )

    # Tools always loop back to Generate
    workflow.add_edge("tools", "generate")

    # After storing memory, we're done
    workflow.add_edge("memory_store", END)

    return workflow
