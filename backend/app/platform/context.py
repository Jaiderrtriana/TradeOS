"""
Request-scoped context: correlation ID and (once authenticated) the
caller's user ID, threaded through every log line for the duration of one
request (TRADEOS_BACKEND_BLUEPRINT.md §11; Master Plan Sprint 0.2).

Built directly on structlog's own contextvars support
(TRADEOS_TECHNICAL_STACK.md §7 — structlog is the mandated logging
library) rather than a second, parallel contextvars mechanism.
"""

from uuid import UUID

import structlog


def set_correlation_id(correlation_id: str) -> None:
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def get_correlation_id() -> str | None:
    return structlog.contextvars.get_contextvars().get("correlation_id")


def set_user_id(user_id: UUID) -> None:
    structlog.contextvars.bind_contextvars(user_id=str(user_id))


def get_user_id() -> str | None:
    return structlog.contextvars.get_contextvars().get("user_id")


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
