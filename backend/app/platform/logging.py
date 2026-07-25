"""
Structured logging — structlog, JSON-structured, correlation-ID bound
(TRADEOS_TECHNICAL_STACK.md §7, MANDATORY).

`merge_contextvars` is what makes every bound value in app/platform/context.py
(correlation_id, user_id) appear on every subsequent log line automatically,
without threading them through every function call by hand.
"""

import logging

import structlog


def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger(name)
