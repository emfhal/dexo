"""
src/observability/instrumentation.py
───────────────────────────────────────
Custom spans and decorators for fine-grained tracing of graph nodes,
context loading, and memory retrieval.
"""
from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("langgraph-src", "2.0.0")

F = TypeVar("F", bound=Callable[..., Any])


def traced_node(name: str | None = None) -> Callable[[F], F]:
    """
    Decorator for LangGraph node functions.
    Records node name, user_id, iteration, and any exceptions.

    Usage:
        @traced_node("context_loader")
        async def load_context(state: AgentState) -> dict:
            ...
    """

    def decorator(fn: F) -> F:
        span_name = name or fn.__name__

        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(f"node.{span_name}") as span:
                    _annotate_state_span(span, args)
                    try:
                        result = await fn(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with tracer.start_as_current_span(f"node.{span_name}") as span:
                    _annotate_state_span(span, args)
                    try:
                        result = fn(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        span.record_exception(exc)
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        raise

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def traced_memory(backend: str) -> Callable[[F], F]:
    """Decorator for memory backend calls — records latency and hit/miss."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f"memory.{backend}.{fn.__name__}") as span:
                span.set_attribute("memory.backend", backend)
                t0 = time.perf_counter()
                try:
                    result = await fn(*args, **kwargs)
                    latency_ms = (time.perf_counter() - t0) * 1000
                    span.set_attribute("memory.latency_ms", round(latency_ms, 2))
                    span.set_attribute(
                        "memory.result_count",
                        len(result) if isinstance(result, list) else 1,
                    )
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, str(exc)))
                    raise

        return wrapper  # type: ignore[return-value]

    return decorator


def _annotate_state_span(span: trace.Span, args: tuple[Any, ...]) -> None:
    """Pull common AgentState attributes into span tags if available."""
    if not args:
        return
    state = args[0]
    if hasattr(state, "thread_id"):
        span.set_attribute("src.thread_id", state.thread_id)
    if hasattr(state, "iteration"):
        span.set_attribute("src.iteration", state.iteration)
    if hasattr(state, "auth") and state.auth:
        span.set_attribute("src.user_id", state.auth.user_id)
