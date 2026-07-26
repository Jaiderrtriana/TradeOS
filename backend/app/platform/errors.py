"""
Error envelope + minimal centralized exception handling.

Deliberately minimal, per Sprint 0.2's approved scope: this exists only so
the 401 this sprint's Exit Criteria requires — and an unexpected 500 —
already respect the one error shape TRADEOS_API_SPECIFICATION.md §8
defines. No domain-invariant handling, no business-validation layer: there
are no Use Cases yet to raise either (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md,
Sprint 0.2 scope).
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.platform.context import get_correlation_id
from app.platform.logging import get_logger

logger = get_logger(__name__)


def build_error_envelope(
    code: str, message: str, details: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """The one error shape every failure returns (TRADEOS_API_SPECIFICATION.md §8)."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "trace_id": get_correlation_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


class AppError(Exception):
    """Base for errors that already know their HTTP status and API error code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


class UnauthenticatedError(AppError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__(status_code=401, code="UNAUTHENTICATED", message=message)


class ConflictError(AppError):
    """A request conflicts with existing data or state (e.g., a duplicate
    email, or an action requiring `status = draft` attempted on a
    published version)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=409, code="CONFLICT", message=message)


class NotFoundError(AppError):
    """The referenced resource does not exist."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=404, code="NOT_FOUND", message=message)


class UnprocessableEntityError(AppError):
    """A request is well-formed but violates a business rule (e.g.,
    max_value < min_value, or publishing a version that references an
    inactive criterion) — distinct from Pydantic's own shape-validation
    422s (VALIDATION_FAILED, above)."""

    def __init__(self, message: str) -> None:
        super().__init__(status_code=422, code="UNPROCESSABLE_ENTITY", message=message)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers handlers for route/Use-Case-raised errors (from Phase 1
    onward). Not used by the authentication middleware's own 401 today —
    exceptions raised inside ASGI middleware run outside Starlette's
    ExceptionMiddleware layer and are never delivered here, so that
    middleware builds its response directly with build_error_envelope()
    instead (see app/platform/middleware/authentication.py).
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_envelope(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Layer 1/2 validation (TRADEOS_API_SPECIFICATION.md §9) — shape and
        # range failures FastAPI/Pydantic already caught before any Use
        # Case ran. Reshaped into the one error envelope (§8) rather than
        # FastAPI's own default error body.
        details = [
            {"field": ".".join(str(part) for part in error["loc"][1:]), "issue": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=build_error_envelope(
                "VALIDATION_FAILED", "Request validation failed.", details
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content=build_error_envelope("INTERNAL_ERROR", "An unexpected error occurred."),
        )
