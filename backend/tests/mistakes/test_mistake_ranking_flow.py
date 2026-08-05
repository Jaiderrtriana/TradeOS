"""
Integration tests: `GET /mistakes/ranking` (`TRADEOS_API_SPECIFICATION.md`
§6.9, Sprint 5.2) — run through the real FastAPI app, same client/auth
fixture pattern as tests/trading/test_tag_mistake_flow.py.

Cost/priority formula (approved, Sprint 5.2 pre-analysis — no document
defines one): cost = sum of `r_multiple` across every tagged Trade
(winners included); priority = stable rank by total cost ascending
(most negative/costly first), fixed regardless of the `sort` query
param used to reorder the *displayed* list.
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
    email = f"mistake-rank-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _publish_empty_configuration_version(client, headers) -> None:
    """`RegisterTrade` requires some published Configuration version to
    evaluate against, even with zero criteria/weights — same helper
    pattern as tests/journal/test_journal_flow.py."""
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
    client, headers, *, entry_price: float = 100.0, stop_loss: float = 95.0
) -> str:
    payload = {
        "market": "EURUSD",
        "direction": "long",
        "status": "open",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "entered_at": "2026-01-01T00:00:00Z",
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


async def test_ranking_is_empty_for_a_fresh_user(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []


async def test_ranking_computes_frequency_and_total_cost_r_across_all_tagged_trades(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    suffix = uuid.uuid4().hex[:8]
    tag_id = await _create_mistake_tag(client, headers, f"FOMO-{suffix}")

    # Long, entry 100 / stop 95 (risk = 5): exit 110 -> r = +2.0
    trade_a = await _register_trade(client, headers)
    await _close_trade(client, headers, trade_a, result="tp", exit_price=110.0)
    await _tag_mistake(client, headers, trade_a, tag_id)

    # Long, entry 100 / stop 95: exit 95 (at stop) -> r = -1.0
    trade_b = await _register_trade(client, headers)
    await _close_trade(client, headers, trade_b, result="sl", exit_price=95.0)
    await _tag_mistake(client, headers, trade_b, tag_id)

    response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    entry = body[0]
    assert entry["catalog_entry_id"] == tag_id
    assert entry["frequency"] == 2
    assert entry["total_cost_r"] == 1.0  # 2.0 + (-1.0), winners included
    assert entry["priority"] == 1


async def test_open_trade_counts_toward_frequency_but_not_cost(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    suffix = uuid.uuid4().hex[:8]
    tag_id = await _create_mistake_tag(client, headers, f"Revenge-{suffix}")

    trade = await _register_trade(client, headers)  # never closed
    await _tag_mistake(client, headers, trade, tag_id)

    response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    body = response.json()
    assert len(body) == 1
    assert body[0]["frequency"] == 1
    assert body[0]["total_cost_r"] is None


async def test_priority_is_stable_across_different_sort_orders(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    suffix = uuid.uuid4().hex[:8]

    fomo_id = await _create_mistake_tag(client, headers, f"FOMO-{suffix}")
    moved_stop_id = await _create_mistake_tag(client, headers, f"MovedStop-{suffix}")
    revenge_id = await _create_mistake_tag(client, headers, f"Revenge-{suffix}")

    # FOMO: two trades, net cost = +2.0 + -1.0 = +1.0, frequency 2.
    trade_a = await _register_trade(client, headers)
    await _close_trade(client, headers, trade_a, result="tp", exit_price=110.0)
    await _tag_mistake(client, headers, trade_a, fomo_id)

    trade_b = await _register_trade(client, headers)
    await _close_trade(client, headers, trade_b, result="sl", exit_price=95.0)
    await _tag_mistake(client, headers, trade_b, fomo_id)
    await _tag_mistake(client, headers, trade_b, moved_stop_id)  # MovedStop: cost -1.0, freq 1.

    trade_c = await _register_trade(client, headers)  # Revenge: open, freq 1, cost None.
    await _tag_mistake(client, headers, trade_c, revenge_id)

    # Default sort (cost ascending, most costly first): MovedStop(-1.0) <
    # FOMO(+1.0) < Revenge(None, sorts last).
    default_response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    default_body = default_response.json()
    priority_by_tag = {entry["catalog_entry_id"]: entry["priority"] for entry in default_body}
    assert [entry["catalog_entry_id"] for entry in default_body] == [
        moved_stop_id,
        fomo_id,
        revenge_id,
    ]
    assert priority_by_tag[moved_stop_id] == 1
    assert priority_by_tag[fomo_id] == 2
    assert priority_by_tag[revenge_id] == 3

    # sort=-frequency reorders the *rows* (FOMO has the highest
    # frequency), but every tag's own `priority` value must stay
    # identical to the default-sort values above -- the core Sprint 5.2
    # architectural decision under test.
    freq_response = await client.get(
        "/api/v1/mistakes/ranking", params={"sort": "-frequency"}, headers=headers
    )
    freq_body = freq_response.json()
    assert freq_body[0]["catalog_entry_id"] == fomo_id
    for entry in freq_body:
        assert entry["priority"] == priority_by_tag[entry["catalog_entry_id"]]

    # sort=-cost reverses the cost ordering entirely -- same invariant.
    cost_desc_response = await client.get(
        "/api/v1/mistakes/ranking", params={"sort": "-cost"}, headers=headers
    )
    cost_desc_body = cost_desc_response.json()
    assert [entry["catalog_entry_id"] for entry in cost_desc_body] == [
        fomo_id,
        moved_stop_id,
        revenge_id,
    ]
    for entry in cost_desc_body:
        assert entry["priority"] == priority_by_tag[entry["catalog_entry_id"]]


async def test_deactivated_tag_still_appears_with_its_historical_occurrences(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    suffix = uuid.uuid4().hex[:8]
    tag_id = await _create_mistake_tag(client, headers, f"OldMistake-{suffix}")

    trade = await _register_trade(client, headers)
    await _close_trade(client, headers, trade, result="sl", exit_price=95.0)
    await _tag_mistake(client, headers, trade, tag_id)

    deactivate_response = await client.post(
        f"/api/v1/catalogs/{tag_id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200, deactivate_response.text

    response = await client.get("/api/v1/mistakes/ranking", headers=headers)
    body = response.json()
    assert len(body) == 1
    assert body[0]["catalog_entry_id"] == tag_id
    assert body[0]["is_active"] is False
    assert body[0]["frequency"] == 1
    assert body[0]["total_cost_r"] == -1.0


async def test_ranking_is_scoped_to_the_requesting_user(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers_a)
    suffix = uuid.uuid4().hex[:8]
    tag_id = await _create_mistake_tag(client, headers_a, f"Shared-{suffix}")

    trade = await _register_trade(client, headers_a)
    await _tag_mistake(client, headers_a, trade, tag_id)

    response = await client.get("/api/v1/mistakes/ranking", headers=headers_b)
    assert response.json() == []


async def test_ranking_requires_authentication(client):
    response = await client.get("/api/v1/mistakes/ranking")
    assert response.status_code == 401


async def test_ranking_rejects_unsupported_sort(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/mistakes/ranking", params={"sort": "name"}, headers=headers
    )
    assert response.status_code == 422
