"""
Integration tests: the Configuration Module's full endpoint surface
(TRADEOS_API_SPECIFICATION.md §6.6), run through the real FastAPI app.

Uses unique IDs/labels per test (uuid-suffixed) rather than fixed ones,
since `postgres_container` is session-scoped and prior tests' rows persist
across the whole test session (see tests/conftest.py's db_session
fixture) — the same convention Identity's tests already use (unique
emails per test).
"""

import uuid

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


async def _auth_headers(client) -> dict[str, str]:
    email = f"config-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_list_engine_types_returns_the_five_seeded_engines(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/configuration/engine-types", headers=headers)
    assert response.status_code == 200
    codes = {row["code"] for row in response.json()}
    assert codes == {"confidence", "quality", "execution", "market_context", "bias"}
    bias = next(row for row in response.json() if row["code"] == "bias")
    assert bias["is_signed"] is True


async def test_list_scoring_profiles_returns_the_three_seeded_profiles(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/configuration/scoring-profiles", headers=headers)
    assert response.status_code == 200
    codes = {row["code"] for row in response.json()}
    assert codes == {"day_trading", "swing_trading", "scalping"}


async def test_endpoints_require_authentication(client):
    response = await client.get("/api/v1/configuration/engine-types")
    assert response.status_code == 401


async def test_create_scoring_profile_then_appears_in_list(client):
    headers = await _auth_headers(client)
    code = f"custom_{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/configuration/scoring-profiles",
        json={"code": code, "display_name": "Custom Profile"},
        headers=headers,
    )
    assert response.status_code == 201

    listed = await client.get("/api/v1/configuration/scoring-profiles", headers=headers)
    assert any(row["code"] == code for row in listed.json())


async def test_create_scoring_profile_duplicate_code_returns_409(client):
    headers = await _auth_headers(client)
    code = f"dup_{uuid.uuid4().hex[:8]}"
    payload = {"code": code, "display_name": "Duplicate"}
    first = await client.post(
        "/api/v1/configuration/scoring-profiles", json=payload, headers=headers
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/configuration/scoring-profiles", json=payload, headers=headers
    )
    assert second.status_code == 409


async def test_create_scoring_criterion_success(client):
    headers = await _auth_headers(client)
    criterion_id = f"confidence.test_{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "confidence",
            "name": "Test Criterion",
            "source_field": "test_field",
            "min_value": 0,
            "max_value": 100,
            "category_map": {"Yes": 100, "No": 0},
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == criterion_id
    assert body["is_active"] is True


async def test_create_scoring_criterion_max_less_than_min_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": f"confidence.invalid_{uuid.uuid4().hex[:8]}",
            "engine_type_code": "confidence",
            "name": "Invalid",
            "source_field": "invalid_field",
            "min_value": 100,
            "max_value": 0,
        },
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_scoring_criterion_unknown_engine_type_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": f"unknown.criterion_{uuid.uuid4().hex[:8]}",
            "engine_type_code": "not_a_real_engine",
            "name": "Bad Engine",
            "source_field": "bad_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_scoring_criterion_duplicate_id_returns_409(client):
    headers = await _auth_headers(client)
    criterion_id = f"confidence.dup_{uuid.uuid4().hex[:8]}"
    payload = {
        "id": criterion_id,
        "engine_type_code": "confidence",
        "name": "Dup",
        "source_field": "dup_field",
        "min_value": 0,
        "max_value": 100,
    }
    first = await client.post(
        "/api/v1/configuration/scoring-criteria", json=payload, headers=headers
    )
    assert first.status_code == 201
    second = await client.post(
        "/api/v1/configuration/scoring-criteria", json=payload, headers=headers
    )
    assert second.status_code == 409


async def test_list_scoring_criteria_filters_by_engine_type(client):
    headers = await _auth_headers(client)
    criterion_id = f"quality.filter_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "quality",
            "name": "Filter Test",
            "source_field": "filter_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    response = await client.get(
        "/api/v1/configuration/scoring-criteria", params={"engine_type": "quality"}, headers=headers
    )
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()}
    assert criterion_id in ids
    assert all(row["engine_type_code"] == "quality" for row in response.json())


async def test_update_scoring_criterion_partial_update_preserves_untouched_fields(client):
    headers = await _auth_headers(client)
    criterion_id = f"execution.update_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "execution",
            "name": "Original Name",
            "description": "Original description",
            "source_field": "update_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    response = await client.patch(
        f"/api/v1/configuration/scoring-criteria/{criterion_id}",
        json={"name": "New Name"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "New Name"
    assert body["description"] == "Original description"


async def test_deactivate_scoring_criterion(client):
    headers = await _auth_headers(client)
    criterion_id = f"execution.deactivate_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "execution",
            "name": "To Deactivate",
            "source_field": "deactivate_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    response = await client.post(
        f"/api/v1/configuration/scoring-criteria/{criterion_id}/deactivate", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


async def test_create_draft_configuration_version(client):
    headers = await _auth_headers(client)
    label = f"v-{uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/configuration/versions", json={"version_label": label}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"


async def test_create_draft_duplicate_label_returns_409(client):
    headers = await _auth_headers(client)
    label = f"v-{uuid.uuid4().hex[:8]}"
    payload = {"version_label": label}
    first = await client.post("/api/v1/configuration/versions", json=payload, headers=headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/configuration/versions", json=payload, headers=headers)
    assert second.status_code == 409


async def test_update_draft_weight_add_then_update(client):
    headers = await _auth_headers(client)
    criterion_id = f"confidence.weight_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "confidence",
            "name": "Weight Test",
            "source_field": "weight_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    version_id = version_response.json()["id"]

    added = await client.post(
        f"/api/v1/configuration/versions/{version_id}/weights",
        json={"criterion_id": criterion_id, "profile_code": "day_trading", "weight": 0.3},
        headers=headers,
    )
    assert added.status_code == 200
    assert added.json()["weight"] == 0.3

    updated = await client.post(
        f"/api/v1/configuration/versions/{version_id}/weights",
        json={"criterion_id": criterion_id, "profile_code": "day_trading", "weight": 0.6},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["weight"] == 0.6
    assert updated.json()["id"] == added.json()["id"]


async def test_update_draft_weight_on_published_version_returns_409(client):
    """TRADEOS_DATABASE_DESIGN.md §6.6: published versions are immutable."""
    headers = await _auth_headers(client)
    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    version_id = version_response.json()["id"]
    publish_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert publish_response.status_code == 200

    criterion_id = f"confidence.locked_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "confidence",
            "name": "Locked",
            "source_field": "locked_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/weights",
        json={"criterion_id": criterion_id, "profile_code": "day_trading", "weight": 0.1},
        headers=headers,
    )
    assert response.status_code == 409


async def test_publish_non_draft_version_returns_409(client):
    headers = await _auth_headers(client)
    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    version_id = version_response.json()["id"]
    first_publish = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert first_publish.status_code == 200

    second_publish = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert second_publish.status_code == 409


async def test_publish_referencing_inactive_criterion_returns_422(client):
    headers = await _auth_headers(client)
    criterion_id = f"confidence.inactive_{uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": criterion_id,
            "engine_type_code": "confidence",
            "name": "Will Deactivate",
            "source_field": "will_deactivate_field",
            "min_value": 0,
            "max_value": 100,
        },
        headers=headers,
    )
    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    version_id = version_response.json()["id"]
    await client.post(
        f"/api/v1/configuration/versions/{version_id}/weights",
        json={"criterion_id": criterion_id, "profile_code": "day_trading", "weight": 0.5},
        headers=headers,
    )
    await client.post(
        f"/api/v1/configuration/scoring-criteria/{criterion_id}/deactivate", headers=headers
    )

    response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert response.status_code == 422


async def test_publishing_a_second_draft_supersedes_the_first(client):
    """The Master Plan's own named Sprint 2.1 Exit Criteria: exactly one
    ScoringConfigurationVersion has status = published; publishing a
    second draft correctly supersedes it (Domain Invariant DI-06/DI-07)."""
    headers = await _auth_headers(client)

    first_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    first_id = first_response.json()["id"]
    first_published = await client.post(
        f"/api/v1/configuration/versions/{first_id}/publish", headers=headers
    )
    assert first_published.status_code == 200
    assert first_published.json()["status"] == "published"

    second_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    second_id = second_response.json()["id"]
    second_published = await client.post(
        f"/api/v1/configuration/versions/{second_id}/publish", headers=headers
    )
    assert second_published.status_code == 200
    assert second_published.json()["status"] == "published"

    versions = await client.get("/api/v1/configuration/versions", headers=headers)
    by_id = {row["id"]: row for row in versions.json()}
    assert by_id[first_id]["status"] == "superseded"
    assert by_id[second_id]["status"] == "published"
    published_count = sum(1 for row in versions.json() if row["status"] == "published")
    assert published_count == 1
