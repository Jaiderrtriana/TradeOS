"""
Correlation ID middleware — generates or honors an inbound X-Correlation-ID,
binds it to the request-scoped logging context, and returns it on every
response (TRADEOS_BACKEND_BLUEPRINT.md §11; Master Plan Sprint 0.2).

Implemented as plain ASGI middleware, not Starlette's BaseHTTPMiddleware:
BaseHTTPMiddleware runs the downstream app in a separate anyio task, which
does not reliably propagate contextvars set beforehand. Plain ASGI keeps
everything in one call stack, so the bound correlation_id is guaranteed
visible to every middleware/handler downstream — including a 401 rejected
by AuthenticationMiddleware, which is the whole point of this sprint's
"even rejected requests stay correlated" requirement.
"""

import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.platform.context import clear_context, set_correlation_id
from app.platform.logging import get_logger

logger = get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        correlation_id = headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        set_correlation_id(correlation_id)

        async def send_with_correlation_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                response_headers[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        try:
            logger.info("request_received", method=scope.get("method"), path=scope.get("path"))
            await self.app(scope, receive, send_with_correlation_id)
            logger.info("request_completed")
        finally:
            clear_context()
