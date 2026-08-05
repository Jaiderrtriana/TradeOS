"""
Integration tests: `GET /dashboard` (`TRADEOS_API_SPECIFICATION.md`
§6.12, Sprint 8.1) — run through the real FastAPI app, same
client/auth fixture pattern as tests/mistakes/test_mistake_ranking_flow.py.

Master Plan §10's own named regression rule for Phase 8: "Dashboard
never duplicates a number differently than its source endpoint returns
it" — `test_dashboard_matches_calling_each_source_endpoint_separately`
is that regression test, byte-for-byte.
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
    email = f"dashboard-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _publish_empty_configuration_version(client, headers) -> None:
    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert version_response.status_code == 201, version_response.text
    version_id = version_response.json()["id"]
    publish_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert publish_response.status_code == 200, publish_response.text


async def _register_trade(
    client, headers, *, entered_at: str = "2026-01-01T00:00:00Z"
) -> str:
    payload = {
        "market": "EURUSD",
        "direction": "long",
        "status": "open",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "entered_at": entered_at,
        "scoring_profile": PROFILE,
    }
    response = await client.post("/api/v1/trades", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _close_trade(client, headers, trade_id: str, *, result: str, exit_price: float) -> None:
    response = await client.post(
        f"/api/v1/trades/{trade_id}/close",
        json={
            "result": result,
            "exit_price": exit_price,
            "realized_pnl": 0.0,
            "closed_at": "2026-01-02T00:00:00Z",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def _create_mistake_tag(client, headers, name: str) -> str:
    response = await client.post(
        "/api/v1/catalogs", json={"kind": "mistake_tag", "name": name}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _tag_mistake(client, headers, trade_id: str, catalog_entry_id: str) -> None:
    response = await client.post(
        f"/api/v1/trades/{trade_id}/mistakes",
        json={"catalog_entry_id": catalog_entry_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text


async def test_dashboard_is_empty_shaped_for_a_fresh_user(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["overview"]["win_rate"] is None
    assert body["overview"]["total_pnl"] == 0.0
    assert body["rolling"]["window"] == 10
    assert body["rolling"]["rolling"]["win_rate"] is None
    assert body["top_mistakes"] == []
    assert body["recent_trades"] == []


async def test_dashboard_requires_authentication(client):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 401


async def test_dashboard_recent_trades_respects_limit_and_most_recent_first(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    trade_ids = []
    for day in range(1, 8):  # 7 trades registered, limit is 5
        trade_id = await _register_trade(client, headers, entered_at=f"2026-01-0{day}T00:00:00Z")
        trade_ids.append(trade_id)

    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    recent_trades = response.json()["recent_trades"]

    assert len(recent_trades) == 5
    assert [t["id"] for t in recent_trades] == list(reversed(trade_ids))[:5]


async def test_dashboard_top_mistakes_limited_to_three(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    tag_ids = []
    for index in range(4):  # 4 distinct mistake tags tagged, only top 3 expected
        suffix = uuid.uuid4().hex[:8]
        tag_id = await _create_mistake_tag(client, headers, f"Mistake{index}-{suffix}")
        tag_ids.append(tag_id)
        trade_id = await _register_trade(client, headers)
        await _close_trade(
            client, headers, trade_id, result="sl", exit_price=95.0 - index
        )  # increasingly costly, so ranking order is deterministic
        await _tag_mistake(client, headers, trade_id, tag_id)

    response = await client.get("/api/v1/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    top_mistakes = response.json()["top_mistakes"]

    assert len(top_mistakes) == 3
    ranking_response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    full_ranking = ranking_response.json()
    assert top_mistakes == full_ranking[:3]


async def test_dashboard_matches_calling_each_source_endpoint_separately(client):
    """Master Plan §10's own regression rule for Phase 8: "Dashboard
    never duplicates a number differently than its source endpoint
    returns it."""
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    tag_id = await _create_mistake_tag(client, headers, f"Tag-{uuid.uuid4().hex[:8]}")
    trade_a = await _register_trade(client, headers, entered_at="2026-01-01T00:00:00Z")
    await _close_trade(client, headers, trade_a, result="tp", exit_price=110.0)
    await _tag_mistake(client, headers, trade_a, tag_id)
    trade_b = await _register_trade(client, headers, entered_at="2026-01-02T00:00:00Z")
    await _close_trade(client, headers, trade_b, result="sl", exit_price=95.0)

    dashboard_response = await client.get("/api/v1/dashboard", headers=headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard_body = dashboard_response.json()

    overview_response = await client.get("/api/v1/statistics/overview", headers=headers)
    assert dashboard_body["overview"] == overview_response.json()

    rolling_response = await client.get(
        "/api/v1/statistics/rolling", params={"window": 10}, headers=headers
    )
    assert dashboard_body["rolling"] == rolling_response.json()

    ranking_response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    assert dashboard_body["top_mistakes"] == ranking_response.json()[:3]

    trades_response = await client.get(
        "/api/v1/trades", params={"limit": 5, "sort": "-entered_at"}, headers=headers
    )
    trades_by_id = {t["id"]: t for t in trades_response.json()["data"]}
    for entry in dashboard_body["recent_trades"]:
        full_trade = trades_by_id[entry["id"]]
        assert entry["market"] == full_trade["market"]
        assert entry["direction"] == full_trade["direction"]
        assert entry["status"] == full_trade["status"]
        assert entry["result"] == full_trade["result"]
        assert entry["r_multiple"] == full_trade["r_multiple"]
