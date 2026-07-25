"""
Proves Sprint 0.2's Exit Criteria (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md,
Phase 0, Sprint 0.2): a request without a bearer token is rejected at the
boundary layer — never inside a route/Use Case.

Uses a throwaway route mounted only within this test module, the same
pattern Sprint 0.1 used for the event dispatcher — no real business route
exists yet to test against.
"""

from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.platform.middleware.authentication import AuthenticationMiddleware
from app.platform.middleware.correlation_id import CorrelationIdMiddleware
from app.platform.security.jwt import create_access_token


def _build_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected_route() -> dict:
        return {"ok": True}

    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    return app


def test_request_without_token_is_rejected_with_401_before_reaching_route():
    client = TestClient(_build_test_app())
    response = client.get("/protected")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"


def test_request_with_malformed_authorization_header_is_rejected():
    client = TestClient(_build_test_app())
    response = client.get("/protected", headers={"Authorization": "NotBearer xyz"})
    assert response.status_code == 401


def test_request_with_invalid_token_is_rejected():
    client = TestClient(_build_test_app())
    response = client.get("/protected", headers={"Authorization": "Bearer garbage-token"})
    assert response.status_code == 401


def test_request_with_valid_token_passes_through():
    client = TestClient(_build_test_app())
    token = create_access_token(uuid4())
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
