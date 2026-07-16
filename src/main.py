"""
src/main.py
──────────────
FastAPI application entry point.
Uses lifespan to manage all async resources (DB pool, OTEL, context loader warm-up).
Exposes:
  POST /chat          — main src invocation (streaming or blocking)
  POST /chat/resume   — resume an interrupted graph (approval/followup)
  GET  /health        — liveness probe
  GET  /context/debug — inspect current context for a thread (dev only)
"""
from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated, Any

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pydantic import BaseModel

from src.config import get_settings
from src.context.loader import AdvancedContextLoader
from src.graph.builder import build_graph
from src.graph.state import AgentState
from src.memory.manager import MemoryManager
from src.observability.setup import bootstrap_otel, instrument_fastapi
from src.observability.logging import configure_logging
from src.security.middleware import AuthLoggingMiddleware, get_current_user
from src.security.rbac import RBACContext

# Load config early so we fail fast on invalid ENV
cfg = get_settings()
configure_logging(cfg.server.log_level, cfg.server.log_pretty)

log = structlog.get_logger()

# ── Application State ─────────────────────────────────────────────────────────
class AppState:
    memory: MemoryManager
    context_loader: AdvancedContextLoader
    graph: Any   # Compiled LangGraph


app_state = AppState()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    cfg = get_settings()

    # 1. Observability first — must be before any instrumented code
    bootstrap_otel(cfg.observability)
    log.info("OTEL bootstrapped.")

    # 2. Memory backends
    app_state.memory = MemoryManager(cfg.database, cfg.memory)
    await app_state.memory.startup()
    log.info("MemoryManager ready.")

    # 3. Context loader warm-up (pre-loads rules, skills, MCP tools)
    app_state.context_loader = AdvancedContextLoader(cfg.context, app_state.memory)
    await app_state.context_loader.warm_up()
    log.info("ContextLoader warmed up.")

    # 4. Build graph with Postgres checkpointer
    async with app_state.memory.postgres.checkpointer() as checkpointer:
        workflow = build_graph(app_state.memory, app_state.context_loader)
        app_state.graph = workflow.compile(
            checkpointer=checkpointer,
            interrupt_before=["tools"],   # Pause before tool execution for approval
        )
        log.info("LangGraph compiled with Postgres checkpointer.")

        yield  # ← Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await app_state.memory.shutdown()
    log.info("Shutdown complete.")


# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="LangGraph Agent API",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(AuthLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_fastapi(app)


# ── Request / Response Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    stream: bool = False
    max_iterations: int = 10


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    context_budget: dict[str, Any] | None = None
    interrupted: bool = False
    interrupt_payload: dict[str, Any] | None = None


class ResumeRequest(BaseModel):
    thread_id: str
    resume_value: str   # The human's answer to the interrupt (approval / followup)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    rbac: Annotated[RBACContext, Depends(get_current_user)],
    request: Request,
) -> ChatResponse:
    """Main src invocation endpoint."""
    rbac.require("src:write")

    thread_id = body.thread_id or str(uuid.uuid4())
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    initial_state = AgentState(
        messages=[HumanMessage(content=body.message)],
        thread_id=thread_id,
        raw_token=token,
        max_iterations=body.max_iterations,
    )

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await app_state.graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        log.error("Graph invocation failed", error=str(exc), thread_id=thread_id)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    # Check for LangGraph interrupt
    state = await app_state.graph.aget_state(config)
    interrupted = bool(state.tasks)  # Pending tasks = graph is interrupted

    last_ai = next(
        (m for m in reversed(result["messages"]) if hasattr(m, "content") and not hasattr(m, "type")),
        None,
    )
    response_text = last_ai.content if last_ai else "No response generated."
    budget = result.get("context", {})
    budget_dict = None
    if hasattr(budget, "budget"):
        b = budget.budget
        budget_dict = {
            "used_pct": b.used_pct,
            "total_tokens": b.total_tokens,
            "budget_limit": b.budget_limit,
        }

    return ChatResponse(
        thread_id=thread_id,
        response=response_text if isinstance(response_text, str) else str(response_text),
        context_budget=budget_dict,
        interrupted=interrupted,
        interrupt_payload=state.tasks[0].interrupts[0].value if interrupted and state.tasks else None,
    )


@app.post("/chat/resume", response_model=ChatResponse)
async def resume_chat(
    body: ResumeRequest,
    rbac: Annotated[RBACContext, Depends(get_current_user)],
    request: Request,
) -> ChatResponse:
    """Resume a graph that was interrupted (awaiting approval or followup)."""
    rbac.require("src:write")

    config = {"configurable": {"thread_id": body.thread_id}}
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()

    # Resume the graph by providing the human's response
    result = await app_state.graph.ainvoke(
        {"resume_value": body.resume_value},
        config=config,
    )

    last_ai = next(
        (m for m in reversed(result.get("messages", [])) if hasattr(m, "content")),
        None,
    )
    return ChatResponse(
        thread_id=body.thread_id,
        response=last_ai.content if last_ai else "",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}


@app.get("/context/debug/{thread_id}")
async def debug_context(
    thread_id: str,
    rbac: Annotated[RBACContext, Depends(get_current_user)],
) -> dict[str, Any]:
    """Dev-only: inspect context budget for a specific thread."""
    if get_settings().server.environment == "production":
        raise HTTPException(status_code=404)
    rbac.require("src:read")

    config = {"configurable": {"thread_id": thread_id}}
    state = await app_state.graph.aget_state(config)
    if not state.values:
        raise HTTPException(status_code=404, detail="Thread not found.")

    ctx = state.values.get("context")
    if ctx and hasattr(ctx, "budget"):
        b = ctx.budget
        return {
            "thread_id": thread_id,
            "budget": {
                "used_pct": b.used_pct,
                "total_tokens": b.total_tokens,
                "budget_limit": b.budget_limit,
                "sections": {
                    "system_prompt": b.system_prompt_tokens,
                    "tool_definitions": b.tool_definitions_tokens,
                    "rules": b.rules_tokens,
                    "skills": b.skills_tokens,
                    "mcp": b.mcp_tokens,
                    "subagents": b.subagent_tokens,
                    "summary": b.summary_tokens,
                    "conversation": b.conversation_tokens,
                },
            },
        }
    return {"thread_id": thread_id, "context": "unavailable"}
