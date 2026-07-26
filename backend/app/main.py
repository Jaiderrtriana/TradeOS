"""
TradeOS backend — entry point.

Sprint 1.1 adds the first real business router: Identity's four
Authentication endpoints (TRADEOS_API_SPECIFICATION.md §6.1). Every other
module's presentation layer is still empty scaffolding.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.identity.presentation.router import router as identity_router
from app.platform.errors import register_exception_handlers
from app.platform.events.dispatcher import dispatcher
from app.platform.logging import configure_logging
from app.platform.middleware.authentication import AuthenticationMiddleware
from app.platform.middleware.correlation_id import CorrelationIdMiddleware

configure_logging()

# Endpoints TRADEOS_API_SPECIFICATION.md §6.1 explicitly marks
# "Auth Required: No" — register/login/refresh issue or exchange
# credentials themselves, so they cannot require an access token to reach.
# /auth/logout is deliberately absent: it requires a valid access token.
PUBLIC_PATHS = frozenset(
    {
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
    }
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The dispatcher is a module-level singleton (app/platform/events/dispatcher.py);
    # binding it here makes its wiring an explicit, visible part of
    # application startup rather than an implicit import-time side effect.
    app.state.event_dispatcher = dispatcher
    yield


app = FastAPI(
    title="TradeOS API",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(identity_router, prefix="/api/v1")

# Middleware order matters: Starlette runs the LAST-added middleware
# OUTERMOST (first on the way in), so CorrelationIdMiddleware — added last
# — always runs before AuthenticationMiddleware. This is what guarantees
# every response, including a 401 rejection, is already correlation-ID
# bound (Sprint 0.2 approved ordering: Correlation ID -> Authentication ->
# FastAPI routing).
app.add_middleware(AuthenticationMiddleware, public_paths=PUBLIC_PATHS)
app.add_middleware(CorrelationIdMiddleware)
