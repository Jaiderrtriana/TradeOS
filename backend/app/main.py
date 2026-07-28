"""
TradeOS backend — entry point.

Sprint 1.1 added Identity's four Authentication endpoints
(TRADEOS_API_SPECIFICATION.md §6.1). Sprint 1.2 adds Preferences'
GET/PATCH (§6.3). Sprint 2.1 adds Configuration's full endpoint surface
(§6.6). Sprint 2.2 adds Catalogs (§6.7) — a second API surface from the
same Configuration backend module. Sprint 3.2 adds Evaluation's
`POST /evaluation/preview` (§6.5). Sprint 4.1 adds Trading's
`POST /trades` (§6.4). Every other module's presentation layer is still
empty scaffolding.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.configuration.presentation.catalogs_router import router as catalogs_router
from app.modules.configuration.presentation.router import router as configuration_router
from app.modules.evaluation.presentation.router import router as evaluation_router
from app.modules.identity.presentation.router import router as identity_router
from app.modules.preferences.presentation.router import router as preferences_router
from app.modules.trading.presentation.router import router as trading_router
from app.platform.config import settings
from app.platform.errors import register_exception_handlers
from app.platform.events.dispatcher import dispatcher
from app.platform.logging import configure_logging
from app.platform.middleware.authentication import AuthenticationMiddleware
from app.platform.middleware.correlation_id import CorrelationIdMiddleware

configure_logging()

# Endpoints TRADEOS_API_SPECIFICATION.md §6.1 explicitly marks
# "Auth Required: No" — register/login/refresh issue or exchange
# credentials themselves, so they cannot require an access token to reach.
# /auth/logout and every /preferences endpoint are deliberately absent:
# both require a valid access token (§6.1, §6.3).
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
app.include_router(preferences_router, prefix="/api/v1")
app.include_router(configuration_router, prefix="/api/v1")
app.include_router(catalogs_router, prefix="/api/v1")
app.include_router(evaluation_router, prefix="/api/v1")
app.include_router(trading_router, prefix="/api/v1")

# Middleware order matters: Starlette runs the LAST-added middleware
# OUTERMOST (first on the way in). Order, outermost to innermost:
# CORS -> Correlation ID -> Authentication -> routing.
#
# CORS must be outermost of all: a cross-origin preflight (OPTIONS) never
# carries the Authorization header, so if AuthenticationMiddleware ran
# first it would reject every preflight with 401 before CORSMiddleware
# ever got a chance to answer it — no browser-based frontend could reach
# this API at all. (No frozen document specifies CORS; it is a pure
# browser cross-origin mechanism, not an architectural decision — see
# CHANGELOG.md, Sprint 1.2.)
#
# Correlation ID still runs before Authentication so even a 401 rejection
# is already correlation-ID bound (Sprint 0.2 approved ordering).
app.add_middleware(AuthenticationMiddleware, public_paths=PUBLIC_PATHS)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
