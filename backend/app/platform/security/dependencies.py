"""
FastAPI dependency exposing the authenticated caller's user_id.

The authentication middleware (app/platform/middleware/authentication.py)
already verified the bearer token and attached user_id to request.state
before any route runs. Routes/Use Cases from Phase 1 onward depend on this
rather than re-reading the Authorization header themselves
(TRADEOS_TECHNICAL_STACK.md §7 — FastAPI-native Depends()).
"""

from uuid import UUID

from starlette.requests import Request


def get_current_user_id(request: Request) -> UUID:
    return request.state.user_id
