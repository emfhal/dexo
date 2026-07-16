"""
src/observability/setup.py
─────────────────────────────
Bootstrap OpenTelemetry once at application startup.
Supports OTLP (gRPC) and Arize Phoenix as backends.
"""
from __future__ import annotations

import logging

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

from src.config import ObservabilityConfig

logger = logging.getLogger(__name__)

_initialized = False


def bootstrap_otel(cfg: ObservabilityConfig) -> None:
    """
    Idempotently initialise the global OTEL provider + exporters.
    Call once from FastAPI lifespan.
    """
    global _initialized
    if _initialized:
        return

    resource = Resource.create(
        {
            "service.name": cfg.service_name,
            "service.version": cfg.service_version,
        }
    )

    # ── Traces ───────────────────────────────────────────────────────────────
    sampler = ParentBasedTraceIdRatio(cfg.sampler_ratio)
    tracer_provider = TracerProvider(resource=resource, sampler=sampler)

    otlp_exporter = OTLPSpanExporter(endpoint=cfg.otlp_endpoint, insecure=True)
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ──────────────────────────────────────────────────────────────
    metric_exporter = OTLPMetricExporter(endpoint=cfg.otlp_endpoint, insecure=True)
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(metric_exporter)],
    )
    metrics.set_meter_provider(meter_provider)

    # ── Auto-instrument HTTP ──────────────────────────────────────────────────
    HTTPXClientInstrumentor().instrument()

    # ── LangChain / LangGraph instrumentation ────────────────────────────────
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("LangChain OTEL instrumentation enabled.")
    except ImportError:
        logger.warning("openinference-instrumentation-langchain not installed — skipping.")

    # ── Optional: Arize Phoenix ───────────────────────────────────────────────
    if getattr(cfg, "phoenix_api_key", None):
        try:
            import phoenix as px

            px.launch_app()
            logger.info("Arize Phoenix connected.")
        except ImportError:
            logger.warning("arize-phoenix not installed — skipping.")

    _initialized = True
    logger.info(
        "OpenTelemetry bootstrapped → %s (sampler=%.2f)",
        cfg.otlp_endpoint,
        cfg.sampler_ratio,
    )


def instrument_fastapi(app: object) -> None:
    """Must be called AFTER bootstrap_otel."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
