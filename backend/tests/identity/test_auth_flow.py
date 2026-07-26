"""
Integration test: the full Register -> Login -> Refresh -> Logout flow
against real persistence (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 1.1
Exit Criteria), run through the real FastAPI app (middleware included) so
the ASGI-level AuthenticationMiddleware public_paths wiring is exercised
too, not just the Use Cases in isolation.

Also covers the Master Plan's own named Phase 1 regression test
(§10): "Refresh-token rotation reuse is rejected (single-use, §4.3)".
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.identity.domain.refresh_token import RefreshToken
from app.modules.identity.infrastructure.repository import RefreshTokenRepository
from app.modules.identity.infrastructure.token_hasher import hash_token
from app.platform.db.session import get_db_session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


async def test_register_login_refresh_logout_flow(client):
    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "trader@example.com", "password": "correct-horse-battery"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["email"] == "trader@example.com"

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "correct-horse-battery"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert logout_response.status_code == 204


async def test_register_response_shape_matches_api_spec_exactly(client):
    """TRADEOS_API_SPECIFICATION.md §6.1: 201, {"user_id": <uuid>, "email": <string>}."""
    response = await client.post(
        "/api/v1/auth/register", json={"email": "shape@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    assert set(response.json().keys()) == {"user_id", "email"}
    UUID(response.json()["user_id"])  # must be a valid UUID string


async def test_login_response_shape_matches_api_spec_exactly(client):
    """§6.1: 200, {"access_token", "refresh_token", "expires_in"}."""
    await client.post(
        "/api/v1/auth/register", json={"email": "shape2@example.com", "password": "password123"}
    )
    response = await client.post(
        "/api/v1/auth/login", json={"email": "shape2@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"access_token", "refresh_token", "expires_in"}
    assert isinstance(body["expires_in"], int)


async def test_error_envelope_shape_matches_api_spec_exactly(client):
    """TRADEOS_API_SPECIFICATION.md §8: {"error": {"code", "message", "details", "trace_id", "timestamp"}}."""
    response = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "irrelevant"}
    )
    assert response.status_code == 401
    body = response.json()
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message", "details", "trace_id", "timestamp"}
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert isinstance(body["error"]["details"], list)


async def test_logout_requires_authentication():
    """Confirms /auth/logout is NOT in AuthenticationMiddleware's public_paths."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as unauthenticated_client:
        response = await unauthenticated_client.post("/api/v1/auth/logout")
    assert response.status_code == 401


async def test_register_with_duplicate_email_is_rejected(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    second_attempt = await client.post(
        "/api/v1/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    assert second_attempt.status_code == 409
    assert second_attempt.json()["error"]["code"] == "CONFLICT"


async def test_login_with_wrong_password_and_unknown_email_are_rejected_identically(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "real@example.com", "password": "password123"}
    )

    wrong_password = await client.post(
        "/api/v1/auth/login", json={"email": "real@example.com", "password": "wrong-password"}
    )
    unknown_email = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]


async def test_rotated_refresh_token_cannot_be_reused(client):
    """The Master Plan's own named Phase 1 regression test (§10)."""
    await client.post(
        "/api/v1/auth/register", json={"email": "rotate@example.com", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "rotate@example.com", "password": "password123"}
    )
    original_refresh_token = login_response.json()["refresh_token"]

    first_use = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original_refresh_token}
    )
    assert first_use.status_code == 200

    reuse_attempt = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original_refresh_token}
    )
    assert reuse_attempt.status_code == 401
    assert reuse_attempt.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_refreshing_an_expired_token_is_rejected(client, db_session):
    register_response = await client.post(
        "/api/v1/auth/register", json={"email": "expired@example.com", "password": "password123"}
    )
    user_id = UUID(register_response.json()["user_id"])

    raw_token = "already-expired-refresh-token"
    await RefreshTokenRepository(db_session).add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
    )
    await db_session.commit()

    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": raw_token})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_logout_revokes_the_refresh_token(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "logout@example.com", "password": "password123"}
    )
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": "logout@example.com", "password": "password123"}
    )
    tokens = login_response.json()

    logout_response = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert logout_response.status_code == 204

    reuse_after_logout = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_after_logout.status_code == 401


async def test_password_is_never_returned_in_any_response(client):
    response = await client.post(
        "/api/v1/auth/register", json={"email": "safe@example.com", "password": "password123"}
    )
    assert "password" not in response.text
    assert "password_hash" not in response.text


async def test_password_shorter_than_minimum_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/register", json={"email": "short@example.com", "password": "short"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    # The 422 handler must never echo the rejected password back
    # (Pydantic's own error detail includes the raw "input" value by
    # default — the handler must deliberately drop it).
    assert "short" not in response.text


async def test_login_and_refresh_never_leak_password_or_tokens_in_error_bodies(client):
    await client.post(
        "/api/v1/auth/register", json={"email": "noleak@example.com", "password": "password123"}
    )
    wrong_password_response = await client.post(
        "/api/v1/auth/login", json={"email": "noleak@example.com", "password": "wrong-password"}
    )
    assert "wrong-password" not in wrong_password_response.text
    assert "password123" not in wrong_password_response.text

    bad_refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"}
    )
    assert "not-a-real-token" not in bad_refresh_response.text
