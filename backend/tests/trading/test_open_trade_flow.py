"""
Integration tests: the `Planned` lifecycle stage introduced in v2.0 (Trade
Entry redesign, Domain Model KDD-07) -- `POST /trades` with `status =
planned`, and the new `POST /trades/{id}/open` transition
(`TRADEOS_API_SPECIFICATION.md` §6.4/§11.1.1). Same client/auth fixture
pattern as tests/trading/test_register_trade_flow.py.
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
    email = f"open-trade-{uuid.uuid4()}@example.com"
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


async def _published_version_with_one_criterion_per_engine(client, headers, suffix: str):
    criteria: dict[str, tuple[str, str]] = {}
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


def _checklist_answers(criteria: dict[str, tuple[str, str]]) -> dict:
    return {
        criteria["confidence"][1]: "Yes",
        criteria["quality"][1]: "No",
        criteria["execution"][1]: "Yes",
        criteria["market_context"][1]: "Yes",
        criteria["bias"][1]: "Bullish",
    }


async def _register_planned_trade(client, headers, market: str = "EURUSD") -> dict:
    response = await client.post(
        "/api/v1/trades",
        json={"market": market, "direction": "long", "status": "planned"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- POST /trades with status = planned ----------------------------------


async def test_register_planned_trade_needs_no_entry_facts_or_scoring_profile(client):
    headers = await _auth_headers(client)
    body = await _register_planned_trade(client, headers)

    assert body["status"] == "planned"
    assert body["entry_price"] is None
    assert body["stop_loss"] is None
    assert body["entered_at"] is None
    assert body["result"] is None
    assert body["evaluation"] is None  # DI-13: no Evaluation yet


async def test_register_planned_trade_rejects_entry_price_present(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/trades",
        json={
            "market": "EURUSD",
            "direction": "long",
            "status": "planned",
            "entry_price": 100.0,
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_get_planned_trade_returns_empty_checklist_and_null_evaluation(client):
    headers = await _auth_headers(client)
    trade = await _register_planned_trade(client, headers)

    response = await client.get(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["checklist_answers"] == {}
    assert body["evaluation"] is None


async def test_get_evaluation_for_planned_trade_returns_404(client):
    headers = await _auth_headers(client)
    trade = await _register_planned_trade(client, headers)

    response = await client.get(f"/api/v1/trades/{trade['id']}/evaluation", headers=headers)
    assert response.status_code == 404


async def test_list_trades_includes_planned_trade_with_null_evaluation(client):
    headers = await _auth_headers(client)
    trade = await _register_planned_trade(client, headers)

    response = await client.get("/api/v1/trades", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    row = next(r for r in body["data"] if r["id"] == trade["id"])
    assert row["status"] == "planned"
    assert row["evaluation"] is None


async def test_list_trades_filters_by_status(client):
    headers = await _auth_headers(client)
    await _register_planned_trade(client, headers, market="EURUSD")

    response = await client.get("/api/v1/trades?status=planned", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["status"] == "planned"

    response = await client.get("/api/v1/trades?status=open", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"] == []


# --- POST /trades/{id}/open ----------------------------------------------


async def test_open_trade_transitions_planned_to_open_and_runs_evaluation(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    trade = await _register_planned_trade(client, headers)
    assert trade["evaluation"] is None

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/open",
        json={
            "entry_price": 100.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
            "stop_loss": 95.0,
            "checklist_answers": _checklist_answers(criteria),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "open"
    assert body["entry_price"] == 100.0
    assert body["stop_loss"] == 95.0
    assert body["entered_at"] is not None
    assert body["evaluation"] is not None
    assert body["evaluation"]["confidence"]["score"] == 100


async def test_open_trade_not_planned_returns_409(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    response = await client.post(
        "/api/v1/trades",
        json={
            "market": "EURUSD",
            "direction": "long",
            "status": "open",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
            "checklist_answers": _checklist_answers(criteria),
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    trade = response.json()

    open_response = await client.post(
        f"/api/v1/trades/{trade['id']}/open",
        json={
            "entry_price": 101.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
        },
        headers=headers,
    )
    assert open_response.status_code == 409
    assert open_response.json()["error"]["code"] == "CONFLICT"


async def test_open_trade_rejects_stop_on_wrong_side(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, _criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    trade = await _register_planned_trade(client, headers)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/open",
        json={
            "entry_price": 100.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
            "stop_loss": 105.0,  # long, stop above entry -- INV-TRADE-01
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_open_trade_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/open",
        json={
            "entry_price": 100.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
        },
        headers=headers,
    )
    assert response.status_code == 404


async def test_open_trade_requires_authentication(client):
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/open",
        json={
            "entry_price": 100.0,
            "entered_at": "2026-01-01T00:00:00Z",
            "scoring_profile": PROFILE,
        },
    )
    assert response.status_code == 401


# --- Statistics fully exclude Planned Trades (Domain Invariant DI-13) ----


async def test_statistics_overview_completely_ignores_planned_trades(client):
    headers = await _auth_headers(client)
    await _register_planned_trade(client, headers)

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["win_rate"] is None
    assert body["expectancy_r"] is None
    assert body["average_r"] is None
    assert body["profit_factor_r"] is None
    assert body["total_pnl"] == 0  # not even realized_pnl=0 from the Planned trade counts
