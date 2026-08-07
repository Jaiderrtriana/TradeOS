"""
Security headers middleware — adds the standard baseline set of HTTP
response headers (TRADEOS_TECHNICAL_STACK.md §14) to every response,
including error responses. Sprint 9.3 (Hardening & Blocking-Question
Resolution).

The backend is a pure JSON API — it never serves HTML, never loads
scripts/styles/images of its own, and is never meant to be framed. This
lets the Content-Security-Policy here be maximally strict (`default-src
'none'`), unlike the frontend's own policy (set separately, in
render.yaml, for the Static Site — that one does need to allow its own
scripts/styles/connections).

Strict-Transport-Security uses max-age=31536000 (1 year) without
includeSubDomains or preload — mirrored from the same reasoning applied
to the frontend's header in render.yaml: MDN's own non-preload example
uses this exact value, and includeSubDomains is deferred until a custom
domain with verified subdomain HTTPS coverage exists.

Implemented as plain ASGI middleware (not Starlette's BaseHTTPMiddleware),
matching the pattern already established by CorrelationIdMiddleware
(app/platform/middleware/correlation_id.py) — no other middleware in
this project uses BaseHTTPMiddleware, and mixing styles for no reason
would be inconsistent for a middleware this simple.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
