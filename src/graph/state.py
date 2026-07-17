"""
src/graph/state.py
────────────────────
Canonical state definition for the LangGraph src.
Everything that flows through the graph lives here.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, ConfigDict, Field

from langchain_core.messages import AnyMessage


class Permission(BaseModel):
    role: str
    scopes: list[str] = Field(default_factory=list)


class AuthContext(BaseModel):
    user_id: str
    session_id: str
    permissions: list[Permission] = Field(default_factory=list)
    claims: dict[str, Any] = Field(default_factory=dict)

    def has_scope(self, scope: str) -> bool:
        return any(scope in p.scopes for p in self.permissions)


class ContextBudget(BaseModel):
    """Mirrors the token-budget bar in the Antigravity UI."""

    total_tokens: int = 0
    system_prompt_tokens: int = 0
    tool_definitions_tokens: int = 0
    rules_tokens: int = 0
    skills_tokens: int = 0
    mcp_tokens: int = 0
    subagent_tokens: int = 0
    summary_tokens: int = 0
    conversation_tokens: int = 0
    budget_limit: int = 16000

    @property
    def used_pct(self) -> float:
        return round(self.total_tokens / self.budget_limit * 100, 1)

    @property
    def is_over_budget(self) -> bool:
        return self.total_tokens > self.budget_limit


class LoadedContext(BaseModel):
    """Assembled context from AdvancedContextLoader."""

    system_prompt: str = ""
    rules: str = ""
    skills: dict[str, str] = Field(default_factory=dict)
    tool_definitions: list[dict[str, Any]] = Field(default_factory=list)
    mcp_tools: list[dict[str, Any]] = Field(default_factory=list)
    subagent_definitions: list[dict[str, Any]] = Field(default_factory=list)
    conversation_summary: str = ""
    budget: ContextBudget = Field(default_factory=ContextBudget)


class ToolApprovalRequest(BaseModel):
    tool_name: str
    tool_input: dict[str, Any]
    reason: str
    requested_at: datetime = Field(default_factory=datetime.utcnow)


class AgentState(BaseModel):
    """
    The single source of truth flowing through every graph node.

    `messages` uses LangGraph's `add_messages` reducer so new messages
    are appended (not replaced) on each node return.
    """

    # ── Core conversation ─────────────────────────────────────────────────
    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    thread_id: str = ""

    # ── Identity / Auth ───────────────────────────────────────────────────
    auth: AuthContext | None = None
    raw_token: str = ""

    # ── Context (assembled by ContextLoader node) ─────────────────────────
    context: LoadedContext = Field(default_factory=LoadedContext)

    # ── Memory retrieval ──────────────────────────────────────────────────
    retrieved_memories: list[dict[str, Any]] = Field(default_factory=list)

    # ── Tool approval flow ────────────────────────────────────────────────
    pending_approval: ToolApprovalRequest | None = None
    approval_decision: Literal["approved", "rejected", "pending"] = "pending"

    # ── Routing ───────────────────────────────────────────────────────────
    next_node: str = ""
    error: str | None = None
    iteration: int = 0
    max_iterations: int = 10

    model_config = ConfigDict(arbitrary_types_allowed=True)
