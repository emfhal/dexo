"""
src/observability/logging.py
──────────────────────────────
Configures structlog for JSON or pretty console output.
"""
import logging
import sys

import structlog

def configure_logging(log_level: str, pretty: bool = True) -> None:
    """Configure standard logging and structlog."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure structlog
    if pretty:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        processors = [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *processors,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )
