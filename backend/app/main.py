"""
TradeOS backend — entry point.

Sprint 0.1 scope only (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md, Phase 0):
wires the in-process Domain Event dispatcher at startup. No routers are
registered yet — every module's presentation layer is still empty
scaffolding (Section 3 of this sprint); authentication middleware and
correlation-ID logging are Sprint 0.2, deliberately not added here.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.platform.events.dispatcher import dispatcher


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
