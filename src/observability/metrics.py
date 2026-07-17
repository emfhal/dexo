"""
src/observability/metrics.py
────────────────────────────────
Application-level metrics: LLM token usage, tool calls, memory latency,
and context budget saturation.
"""

from __future__ import annotations

from opentelemetry import metrics

_meter = metrics.get_meter("langgraph-src", "2.0.0")

# ── LLM ─────────────────────────────────────────────────────────────────────
llm_tokens_total = _meter.create_counter(
    "llm.tokens.total",
    unit="tokens",
    description="Total LLM tokens consumed (prompt + completion).",
)

llm_requests_total = _meter.create_counter(
    "llm.requests.total",
    description="Number of LLM API calls.",
)

llm_latency_histogram = _meter.create_histogram(
    "llm.latency",
    unit="ms",
    description="LLM round-trip latency in milliseconds.",
)

# ── Tools ────────────────────────────────────────────────────────────────────
tool_calls_total = _meter.create_counter(
    "tool.calls.total",
    description="Total tool invocations, by tool name and status.",
)

tool_approval_requests = _meter.create_counter(
    "tool.approval_requests.total",
    description="Number of tool calls requiring human approval.",
)

# ── Memory ───────────────────────────────────────────────────────────────────
memory_retrievals = _meter.create_counter(
    "memory.retrievals.total",
    description="Memory retrieval calls, by backend.",
)

memory_latency_histogram = _meter.create_histogram(
    "memory.latency",
    unit="ms",
    description="Memory backend round-trip latency.",
)

# ── Context ──────────────────────────────────────────────────────────────────
context_budget_gauge = _meter.create_observable_gauge(
    "context.budget.used_pct",
    description="Context window utilization percentage (0-100).",
)

context_tokens_histogram = _meter.create_histogram(
    "context.tokens.loaded",
    unit="tokens",
    description="Tokens loaded per context-loader run.",
)
