"""
src/tools/base.py
────────────────────
SecureTool base class — wraps every LangChain @tool with:
  • RBAC scope enforcement
  • Approval gate for destructive actions
  • OTEL span emission
  • Structured error handling
"""
from __future__ import annotations

import abc
import logging
from typing import Any

from opentelemetry import trace

from src.graph.state import AgentState, ToolApprovalRequest
from src.observability.metrics import tool_approval_requests, tool_calls_total
from src.security.rbac import RBACContext

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("langgraph-src.tools")


class SecureTool(abc.ABC):
    """
    Abstract base for src tools.

    Subclasses implement `_execute()` and declare:
      - `name`: tool identifier
      - `description`: LLM-facing description
      - `required_scope`: RBAC scope string
      - `requires_approval`: whether human sign-off is needed
    """

    name: str
    description: str
    required_scope: str
    requires_approval: bool = False

    def __call__(self, state: AgentState, **kwargs: Any) -> Any:
        """Entry point used by LangGraph ToolNode."""
        with tracer.start_as_current_span(f"tool.{self.name}") as span:
            span.set_attribute("tool.name", self.name)
            span.set_attribute("tool.input_keys", list(kwargs.keys()))

            # ── RBAC ──────────────────────────────────────────────────────────
            if state.auth:
                rbac = RBACContext(
                    user_id=state.auth.user_id,
                    roles=[p.role for p in state.auth.permissions],
                )
                try:
                    rbac.require(self.required_scope)
                except PermissionError as exc:
                    tool_calls_total.add(1, {"tool": self.name, "status": "denied"})
                    span.set_attribute("tool.status", "denied")
                    return {"error": str(exc)}

            # ── Approval gate ─────────────────────────────────────────────────
            if self.requires_approval and state.approval_decision != "approved":
                request = ToolApprovalRequest(
                    tool_name=self.name,
                    tool_input=kwargs,
                    reason=f"Tool '{self.name}' requires explicit human approval.",
                )
                tool_approval_requests.add(1, {"tool": self.name})
                # Return interrupt signal — LangGraph will pause here
                return {"pending_approval": request, "approval_decision": "pending"}

            # ── Execute ───────────────────────────────────────────────────────
            try:
                result = self._execute(**kwargs)
                tool_calls_total.add(1, {"tool": self.name, "status": "success"})
                span.set_attribute("tool.status", "success")
                return result
            except Exception as exc:
                logger.exception("Tool '%s' failed.", self.name)
                tool_calls_total.add(1, {"tool": self.name, "status": "error"})
                span.set_attribute("tool.status", "error")
                span.record_exception(exc)
                return {"error": f"Tool execution failed: {exc}"}

    @abc.abstractmethod
    def _execute(self, **kwargs: Any) -> Any:
        ...
