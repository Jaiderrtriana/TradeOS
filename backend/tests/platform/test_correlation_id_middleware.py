"""
Proves the other half of Sprint 0.2's Exit Criteria: every log line for one
request shares one correlation ID — including a request the authentication
middleware rejects, which is exactly what the approved middleware ordering
(Correlation ID -> Authentication -> routing) exists to guarantee.
"""

from contextlib import contextmanager
from typing import Iterator
from uuid import uuid4

import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.testing import LogCapture

from app.platform.middleware.authentication import AuthenticationMiddleware
from app.platform.middleware.correlation_id import CORRELATION_ID_HEADER, CorrelationIdMiddleware
from app.platform.security.jwt import create_access_token


@contextmanager
def capture_logs_with_context() -> Iterator[list[dict]]:
    """
    Like structlog.testing.capture_logs(), but keeps merge_contextvars in
    the processor chain. capture_logs() replaces *all* processors
    (including merge_contextvars) with a bare capture step, so bound
    context values like correlation_id never reach the captured entries —
    this is required to actually assert on them.
    """
    cap = LogCapture()
    processors = structlog.get_config()["processors"]
    old_processors = processors.copy()
    try:
        processors.clear()
        processors.append(structlog.contextvars.merge_contextvars)
        processors.append(cap)
        structlog.configure(processors=processors)
        yield cap.entries
    finally:
        processors.clear()
        processors.extend(old_processors)
        structlog.configure(processors=processors)


def _build_test_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected_route() -> dict:
        return {"ok": True}

    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    return app


def _authorized_headers() -> dict:
    return {"Authorization": f"Bearer {create_access_token(uuid4())}"}


def test_correlation_id_is_generated_and_returned_when_absent():
    client = TestClient(_build_test_app())
    response = client.get("/protected", headers=_authorized_headers())
    assert CORRELATION_ID_HEADER in response.headers
    assert response.headers[CORRELATION_ID_HEADER]


def test_correlation_id_is_honored_when_supplied():
    client = TestClient(_build_test_app())
    supplied = "test-correlation-id-123"
    headers = _authorized_headers()
    headers[CORRELATION_ID_HEADER] = supplied
    response = client.get("/protected", headers=headers)
    assert response.headers[CORRELATION_ID_HEADER] == supplied


def test_every_log_line_for_one_request_shares_one_correlation_id():
    with capture_logs_with_context() as captured:
        client = TestClient(_build_test_app())
        client.get("/protected", headers=_authorized_headers())

    assert len(captured) >= 2  # at least request_received + request_completed
    correlation_ids = {entry.get("correlation_id") for entry in captured}
    assert len(correlation_ids) == 1
    assert None not in correlation_ids


def test_rejected_request_is_still_correlated():
    with capture_logs_with_context() as captured:
        client = TestClient(_build_test_app())
        response = client.get("/protected")  # no token -> 401

    assert response.status_code == 401
    assert CORRELATION_ID_HEADER in response.headers
    correlation_ids = {entry.get("correlation_id") for entry in captured}
    assert len(correlation_ids) == 1
    assert None not in correlation_ids
