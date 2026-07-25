"""
Authentication middleware — verifies the bearer JWT at the Presentation
boundary. Every request to a domain module passes through this before
reaching any route/Use Case; no domain module implements its own ad hoc
authentication (TRADEOS_SYSTEM_ARCHITECTURE.md §11.1; Master Plan Sprint 0.2).

Plain ASGI middleware, same reasoning as CorrelationIdMiddleware. A
rejection is built and sent directly with build_error_envelope() rather
than raised as an exception: exceptions raised inside ASGI middleware run
outside Starlette's ExceptionMiddleware layer and are never delivered to
handlers registered via register_exception_handlers() — this middleware
must shape its own response to still respect the one error envelope
(TRADEOS_API_SPECIFICATION.md §8).
"""

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.platform.context import set_user_id
from app.platform.errors import build_error_envelope
from app.platform.logging import get_logger
from app.platform.security.jwt import InvalidTokenError, decode_access_token

logger = get_logger(__name__)


def _extract_bearer_token(authorization_header: str | None) -> str | None:
    if not authorization_header:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


class AuthenticationMiddleware:
    def __init__(self, app: ASGIApp, public_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.public_paths = public_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in self.public_paths:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        token = _extract_bearer_token(headers.get("Authorization"))

        if token is None:
            await self._reject(scope, receive, send, "Missing bearer token.")
            return

        try:
            payload = decode_access_token(token)
        except InvalidTokenError as exc:
            await self._reject(scope, receive, send, str(exc))
            return

        set_user_id(payload.user_id)
        scope.setdefault("state", {})["user_id"] = payload.user_id
        await self.app(scope, receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send, reason: str) -> None:
        logger.info("authentication_rejected", reason=reason)
        response = JSONResponse(
            status_code=401,
            content=build_error_envelope("UNAUTHENTICATED", "Authentication required."),
        )
        await response(scope, receive, send)
