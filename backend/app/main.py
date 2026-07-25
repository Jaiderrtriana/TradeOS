"""
TradeOS backend — entry point.

Sprint 0.2 scope only (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md, Phase 0):
wires structured logging, the correlation-ID and authentication middleware
stack, and minimal centralized exception handling. No routers are
registered yet — every module's presentation layer is still empty
scaffolding; login/register/users/roles and every business module remain
untouched, per this sprint's approved scope.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.platform.errors import register_exception_handlers
from app.platform.events.dispatcher import dispatcher
from app.platform.logging import configure_logging
from app.platform.middleware.authentication import AuthenticationMiddleware
from app.platform.middleware.correlation_id import CorrelationIdMiddleware

configure_logging()


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

# Middleware order matters: Starlette runs the LAST-added middleware
# OUTERMOST (first on the way in), so CorrelationIdMiddleware — added last
# — always runs before AuthenticationMiddleware. This is what guarantees
# every response, including a 401 rejection, is already correlation-ID
# bound (Sprint 0.2 approved ordering: Correlation ID -> Authentication ->
# FastAPI routing).
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(CorrelationIdMiddleware)
