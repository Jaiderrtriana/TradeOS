"""
Integration tests: `GET /trades`, `GET /trades/{id}`,
`GET /trades/{id}/evaluation`, `GET /trades/{id}/evaluation/history`
(`TRADEOS_API_SPECIFICATION.md` §6.4/§6.5/§7) — read-endpoint gap closed
ahead of Sprint 4.4, approved. Same client/auth fixture pattern as
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
    email = f"reads-{uuid.uuid4()}@example.com"
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


async def _create_and_publish_version(client, headers, suffix: str, *, criteria=None):
    if criteria is None:
        criteria = {}
        for engine in ("confidence", "quality", "execution", "market_context"):
            criteria[engine] = await _create_criterion(client, headers, engine, suffix)
        criteria["bias"] = await _create_criterion(
            client, headers, "bias", suffix, category_map={"Bullish": 2.5, "Bearish": -2.5}
        )

    version_response = await client.post(
        "/api/v1/configuration/versions", json={"version_label": f"v-{suffix}"}, headers=headers
    )
    assert version_response.status_code == 201, version_response.text
    version_id = version_response.json()["id"]

    for engine, (criterion_id, _) in criteria.items():
        weight_response = await client.post(
            f"/api/v1/configuration/versions/{version_id}/weights",
            json={"criterion_id": criterion_id, "profile_code": PROFILE, "weight": 1.0},
            headers=headers,
        )
        assert weight_response.status_code == 200, weight_response.text

    publish_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert publish_response.status_code == 200, publish_response.text
    return version_id, criteria


def _base_payload(criteria, **overrides) -> dict:
    payload = {
        "market": "EURUSD",
        "direction": "long",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "scoring_profile": PROFILE,
        "checklist_answers": {
            criteria["confidence"][1]: "Yes",
            criteria["quality"][1]: "No",
            criteria["execution"][1]: "Yes",
            criteria["market_context"][1]: "Yes",
            criteria["bias"][1]: "Bullish",
        },
    }
    payload.update(overrides)
    return payload


async def _register_trade(client, headers, criteria, **overrides) -> dict:
    response = await client.post(
        "/api/v1/trades", json=_base_payload(criteria, **overrides), headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- GET /trades -----------------------------------------------------------


async def test_list_trades_empty(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/trades", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {"data": [], "pagination": {"next_cursor": None, "has_more": False}}


async def test_list_trades_returns_summary_shape_ordered_newest_first(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    first = await _register_trade(client, headers, criteria, market="EURUSD")
    second = await _register_trade(client, headers, criteria, market="GBPUSD")

    response = await client.get("/api/v1/trades", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    ids = [row["id"] for row in body["data"]]
    assert ids == [second["id"], first["id"]]  # newest (-entered_at) first

    row = body["data"][0]
    assert "checklist_answers" not in row
    assert "breakdown" not in row["evaluation"]["confidence"]
    assert row["evaluation"]["confidence"]["score"] == 100
    assert row["evaluation"]["confidence"]["grade"] == "A+"


async def test_list_trades_filters_by_direction_and_result(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    await _register_trade(client, headers, criteria, direction="long")
    await _register_trade(
        client, headers, criteria, direction="short", entry_price=100.0, stop_loss=105.0
    )

    response = await client.get("/api/v1/trades?direction=short", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["direction"] == "short"


async def test_list_trades_paginates_with_cursor(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    for i in range(3):
        await _register_trade(client, headers, criteria, market=f"PAIR{i}")

    first_page = await client.get("/api/v1/trades?limit=2", headers=headers)
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert len(first_body["data"]) == 2
    assert first_body["pagination"]["has_more"] is True
    cursor = first_body["pagination"]["next_cursor"]
    assert cursor is not None

    second_page = await client.get(f"/api/v1/trades?limit=2&cursor={cursor}", headers=headers)
    assert second_page.status_code == 200, second_page.text
    second_body = second_page.json()
    assert len(second_body["data"]) == 1
    assert second_body["pagination"]["has_more"] is False

    first_ids = {row["id"] for row in first_body["data"]}
    second_ids = {row["id"] for row in second_body["data"]}
    assert first_ids.isdisjoint(second_ids)


async def test_list_trades_scoped_to_owner(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers_a, suffix)
    await _register_trade(client, headers_a, criteria)

    response = await client.get("/api/v1/trades", headers=headers_b)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


async def test_list_trades_requires_authentication(client):
    response = await client.get("/api/v1/trades")
    assert response.status_code == 401


# --- GET /trades/{id} --------------------------------------------------


async def test_get_trade_returns_full_detail_with_checklist_answers(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    response = await client.get(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == trade["id"]
    assert body["checklist_answers"] == {
        criteria["confidence"][1]: "Yes",
        criteria["quality"][1]: "No",
        criteria["execution"][1]: "Yes",
        criteria["market_context"][1]: "Yes",
        criteria["bias"][1]: "Bullish",
    }
    assert (
        body["evaluation"]["confidence"]["breakdown"][0]["criterion_id"]
        == criteria["confidence"][0]
    )


async def test_get_trade_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.get(f"/api/v1/trades/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_get_trade_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers_a, suffix)
    trade = await _register_trade(client, headers_a, criteria)

    response = await client.get(f"/api/v1/trades/{trade['id']}", headers=headers_b)
    assert response.status_code == 404


async def test_get_trade_soft_deleted_returns_404(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)
    delete_response = await client.delete(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert delete_response.status_code == 204

    response = await client.get(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert response.status_code == 404


# --- GET /trades/{id}/evaluation -----------------------------------------


async def test_get_trade_evaluation_returns_current_snapshot_with_breakdown(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    response = await client.get(f"/api/v1/trades/{trade['id']}/evaluation", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body.keys()) == {"confidence", "quality", "execution", "market_context", "bias"}
    assert body["confidence"]["score"] == 100
    assert len(body["confidence"]["breakdown"]) == 1
    assert "grade" not in body["bias"]


async def test_get_trade_evaluation_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.get(f"/api/v1/trades/{uuid.uuid4()}/evaluation", headers=headers)
    assert response.status_code == 404


# --- GET /trades/{id}/evaluation/history ---------------------------------


async def test_get_trade_evaluation_history_lists_all_snapshots_newest_first(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _v1_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    v2_suffix = f"{suffix}-v2"
    v2_id, _v2_criteria = await _create_and_publish_version(
        client, headers, v2_suffix, criteria=criteria
    )
    reevaluate_response = await client.post(
        f"/api/v1/trades/{trade['id']}/reevaluate",
        json={"scoring_profile": PROFILE, "configuration_version_id": v2_id},
        headers=headers,
    )
    assert reevaluate_response.status_code == 200, reevaluate_response.text

    response = await client.get(f"/api/v1/trades/{trade['id']}/evaluation/history", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 2
    assert body[0]["is_current"] is True
    assert body[0]["configuration_version_id"] == v2_id
    assert body[1]["is_current"] is False
    assert body[1]["configuration_version_id"] == _v1_id
    # newest first: the current (second, later) snapshot appears before
    # the original (first) one.
    assert body[0]["created_at"] >= body[1]["created_at"]


async def test_get_trade_evaluation_history_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.get(
        f"/api/v1/trades/{uuid.uuid4()}/evaluation/history", headers=headers
    )
    assert response.status_code == 404
