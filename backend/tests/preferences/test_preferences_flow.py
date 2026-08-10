"""
Integration test: Preferences auto-creation at registration, GET/PATCH
against real persistence (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 1.2
Exit Criteria), run through the real FastAPI app so both the
AuthenticationMiddleware wiring and the cross-module Identity->Preferences
call (RegisterUseCase -> CreateDefaultPreferencesUseCase) are exercised
end to end, not just the Use Cases in isolation.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
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


async def _register_and_login(client, email: str) -> str:
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    return login_response.json()["access_token"]


async def test_preferences_are_auto_created_with_defaults_at_registration(client):
    """API Spec §6.3: "created automatically with defaults at registration"."""
    access_token = await _register_and_login(client, "autocreate@example.com")

    response = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "theme": "dark",
        "language": "es",
        "notification_settings": {},
        "timezone": None,
    }


async def test_preferences_endpoint_never_404s_for_an_authenticated_user(client):
    access_token = await _register_and_login(client, "never404@example.com")
    response = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code != 404
    assert response.status_code == 200


async def test_get_and_patch_preferences_require_authentication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as unauthenticated_client:
        get_response = await unauthenticated_client.get("/api/v1/preferences")
        patch_response = await unauthenticated_client.patch(
            "/api/v1/preferences", json={"theme": "light"}
        )
    assert get_response.status_code == 401
    assert patch_response.status_code == 401


async def test_patch_updates_theme_and_language(client):
    access_token = await _register_and_login(client, "update@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.patch(
        "/api/v1/preferences", json={"theme": "light", "language": "en"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "theme": "light",
        "language": "en",
        "notification_settings": {},
        "timezone": None,
    }

    get_response = await client.get("/api/v1/preferences", headers=headers)
    assert get_response.json()["theme"] == "light"
    assert get_response.json()["language"] == "en"


async def test_patch_is_partial_untouched_fields_are_preserved(client):
    access_token = await _register_and_login(client, "partial@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    await client.patch("/api/v1/preferences", json={"theme": "light"}, headers=headers)
    response = await client.get("/api/v1/preferences", headers=headers)

    assert response.json()["theme"] == "light"
    assert response.json()["language"] == "es"  # untouched, still the default


async def test_patch_rejects_invalid_theme_enum(client):
    access_token = await _register_and_login(client, "badtheme@example.com")
    response = await client.patch(
        "/api/v1/preferences",
        json={"theme": "neon"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_patch_rejects_invalid_language_enum(client):
    access_token = await _register_and_login(client, "badlang@example.com")
    response = await client.patch(
        "/api/v1/preferences",
        json={"language": "fr"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_two_users_have_independent_preferences(client):
    token_a = await _register_and_login(client, "usera@example.com")
    token_b = await _register_and_login(client, "userb@example.com")

    await client.patch(
        "/api/v1/preferences",
        json={"theme": "light"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    response_b = await client.get(
        "/api/v1/preferences", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response_b.json()["theme"] == "dark"  # user B's own default, unaffected by user A


async def test_patch_persists_valid_iana_timezone(client):
    """Sprint 4 Fase 2 (OQ-7) approved contract: an IANA identifier
    persists and is echoed back on a subsequent GET."""
    access_token = await _register_and_login(client, "tzvalid@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.patch(
        "/api/v1/preferences", json={"timezone": "America/Bogota"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "America/Bogota"

    get_response = await client.get("/api/v1/preferences", headers=headers)
    assert get_response.json()["timezone"] == "America/Bogota"


async def test_patch_rejects_non_iana_timezone(client):
    """Fixed offsets ("UTC-5", "GMT-5") are rejected — only real IANA
    identifiers represent DST correctly (Sprint 4 Fase 2, approved
    contract)."""
    access_token = await _register_and_login(client, "tzinvalid@example.com")
    response = await client.patch(
        "/api/v1/preferences",
        json={"timezone": "UTC-5"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_patch_timezone_is_partial_other_fields_preserved(client):
    access_token = await _register_and_login(client, "tzpartial@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    await client.patch("/api/v1/preferences", json={"theme": "light"}, headers=headers)
    await client.patch("/api/v1/preferences", json={"timezone": "Europe/Madrid"}, headers=headers)
    response = await client.get("/api/v1/preferences", headers=headers)

    assert response.json()["theme"] == "light"  # untouched by the timezone-only patch
    assert response.json()["timezone"] == "Europe/Madrid"
