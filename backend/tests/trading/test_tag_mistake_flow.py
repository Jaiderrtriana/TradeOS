"""
Integration tests: `POST /trades/{id}/mistakes` (`TRADEOS_API_SPECIFICATION.md`
§6.4, Sprint 4.3) and `GET /trades/{id}/mistakes` (Sprint 4.4: closed
alongside the rest of that sprint's read-endpoint gaps, so Trade Detail's
Mistakes section can show already-tagged mistakes) — run through the real
FastAPI app, same client/auth fixture pattern as
tests/trading/test_trade_lifecycle_flow.py.
"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.platform.db.session import get_db_session

PROFILE = "day_trading"


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
    email = f"mistake-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_criterion(client, headers, engine_type_code: str, suffix: str, **overrides):
    payload = {
        "id": f"{engine_type_code}.{suffix}",
        "engine_type_code": engine_type_code,
        "name": f"{engine_type_code} {suffix}",
        "source_field": f"{engine_type_code}_{suffix}_field",
        "min_value": 0,
        "max_value": 100,
        "category_map": {"Yes": 100, "No": 0},
    }
    payload.update(overrides)
    response = await client.post(
        "/api/v1/configuration/scoring-criteria", json=payload, headers=headers
    )
    assert response.status_code == 201, response.text
    return payload["id"], payload["source_field"]


async def _register_trade(client, headers, suffix: str) -> dict:
    criteria: dict[str, tuple[str, str]] = {}
    for engine in ("confidence", "quality", "execution", "market_context"):
        criteria[engine] = await _create_criterion(client, headers, engine, suffix)
    criteria["bias"] = await _create_criterion(
        client, headers, "bias", suffix, category_map={"Bullish": 2.5, "Bearish": -2.5}
    )
    version_response = await client.post(
        "/api/v1/configuration/versions", json={"version_label": f"v-{suffix}"}, headers=headers
    )
    version_id = version_response.json()["id"]
    for engine, (criterion_id, _) in criteria.items():
        await client.post(
            f"/api/v1/configuration/versions/{version_id}/weights",
            json={"criterion_id": criterion_id, "profile_code": PROFILE, "weight": 1.0},
            headers=headers,
        )
    await client.post(f"/api/v1/configuration/versions/{version_id}/publish", headers=headers)

    payload = {
        "market": "EURUSD",
        "direction": "long",
        "status": "open",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "entered_at": "2026-01-01T00:00:00Z",
        "scoring_profile": PROFILE,
        "checklist_answers": {
            criteria["confidence"][1]: "Yes",
            criteria["quality"][1]: "No",
            criteria["execution"][1]: "Yes",
            criteria["market_context"][1]: "Yes",
            criteria["bias"][1]: "Bullish",
        },
    }
    response = await client.post("/api/v1/trades", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _create_catalog_entry(client, headers, *, kind: str, suffix: str) -> str:
    response = await client.post(
        "/api/v1/catalogs", json={"kind": kind, "name": f"{kind}-{suffix}"}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_tag_mistake_success(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)
    mistake_id = await _create_catalog_entry(client, headers, kind="mistake_tag", suffix=suffix)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": mistake_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trade_id"] == trade["id"]
    assert body["catalog_entry_id"] == mistake_id
    assert body["created_at"] is not None


async def test_tag_mistake_rejects_wrong_kind(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)
    strategy_id = await _create_catalog_entry(client, headers, kind="strategy", suffix=suffix)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": strategy_id},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_tag_mistake_rejects_inactive_entry(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)
    mistake_id = await _create_catalog_entry(client, headers, kind="mistake_tag", suffix=suffix)
    deactivate_response = await client.post(
        f"/api/v1/catalogs/{mistake_id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200, deactivate_response.text

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": mistake_id},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_tag_mistake_rejects_missing_catalog_entry(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_tag_mistake_duplicate_returns_409(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)
    mistake_id = await _create_catalog_entry(client, headers, kind="mistake_tag", suffix=suffix)

    first = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": mistake_id},
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": mistake_id},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


async def test_tag_mistake_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/mistakes",
        json={"catalog_entry_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 404


async def test_tag_mistake_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers_a, suffix)
    mistake_id = await _create_catalog_entry(client, headers_a, kind="mistake_tag", suffix=suffix)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/mistakes",
        json={"catalog_entry_id": mistake_id},
        headers=headers_b,
    )
    assert response.status_code == 404


async def test_tag_mistake_requires_authentication(client):
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/mistakes",
        json={"catalog_entry_id": str(uuid.uuid4())},
    )
    assert response.status_code == 401


async def test_list_trade_mistakes_empty(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)

    response = await client.get(f"/api/v1/trades/{trade['id']}/mistakes", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []


async def test_list_trade_mistakes_returns_tagged_entries_newest_first(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers, suffix)
    first_id = await _create_catalog_entry(
        client, headers, kind="mistake_tag", suffix=f"{suffix}-a"
    )
    second_id = await _create_catalog_entry(
        client, headers, kind="mistake_tag", suffix=f"{suffix}-b"
    )

    for mistake_id in (first_id, second_id):
        tag_response = await client.post(
            f"/api/v1/trades/{trade['id']}/mistakes",
            json={"catalog_entry_id": mistake_id},
            headers=headers,
        )
        assert tag_response.status_code == 201, tag_response.text

    response = await client.get(f"/api/v1/trades/{trade['id']}/mistakes", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [entry["catalog_entry_id"] for entry in body] == [second_id, first_id]
    assert all(entry["trade_id"] == trade["id"] for entry in body)


async def test_list_trade_mistakes_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.get(f"/api/v1/trades/{uuid.uuid4()}/mistakes", headers=headers)
    assert response.status_code == 404


async def test_list_trade_mistakes_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    trade = await _register_trade(client, headers_a, suffix)

    response = await client.get(f"/api/v1/trades/{trade['id']}/mistakes", headers=headers_b)
    assert response.status_code == 404


async def test_list_trade_mistakes_requires_authentication(client):
    response = await client.get(f"/api/v1/trades/{uuid.uuid4()}/mistakes")
    assert response.status_code == 401
