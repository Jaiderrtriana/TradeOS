"""
Integration tests: `POST /trades` (TRADEOS_API_SPECIFICATION.md §6.4), run
through the real FastAPI app — Trading's first endpoint. Exercises the
full §11.1 flow: INV-TRADE-01/02 validation, catalog reference validation,
the Trading -> Evaluation cross-module call (via
`build_preview_evaluation_use_case`), persistence of Trade +
ChecklistSnapshot + EvaluationSnapshot (+ breakdown rows) in one
transaction, and the `Idempotency-Key` header (§3.6).

Same client/auth fixture pattern as
tests/evaluation/test_preview_evaluation_flow.py.
"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.modules.trading.infrastructure.models import EvaluationSnapshotModel, TradeModel
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
    email = f"trading-{uuid.uuid4()}@example.com"
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


def _base_payload(suffix: str, criteria: dict[str, tuple[str, str]], **overrides) -> dict:
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
    payload.update(overrides)
    return payload


async def test_register_trade_returns_full_trade_with_evaluation(client, db_session):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )

    payload = _base_payload(
        suffix,
        criteria,
        status="closed",
        exit_price=108.0,
        result="tp",
        realized_pnl=80.0,
        closed_at="2026-01-02T00:00:00Z",
        mfe_price=110.0,
        mae_price=97.0,
    )
    response = await client.post("/api/v1/trades", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["result"] == "tp"
    assert body["closed_at"] is not None  # trader-supplied, echoed back as-is
    assert body["r_multiple"] == 1.6
    assert body["mfe_r"] == 2.0
    assert body["captured_pct"] == 0.8  # raw ratio, never scaled to 80.0
    assert body["evaluation"]["confidence"]["score"] == 100
    assert body["evaluation"]["confidence"]["grade"] == "A+"
    assert body["evaluation"]["bias"]["score"] == 50
    assert "grade" not in body["evaluation"]["bias"]

    trade_id = uuid.UUID(body["id"])
    snapshot_result = await db_session.execute(
        select(EvaluationSnapshotModel).where(EvaluationSnapshotModel.trade_id == trade_id)
    )
    snapshots = snapshot_result.scalars().all()
    assert len(snapshots) == 1
    assert snapshots[0].is_current is True


async def test_register_trade_open_trade_has_null_computed_properties(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    response = await client.post(
        "/api/v1/trades", json=_base_payload(suffix, criteria), headers=headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "open"
    assert body["result"] is None
    assert body["closed_at"] is None
    assert body["r_multiple"] is None
    assert body["captured_pct"] is None


async def test_register_trade_rejects_stop_on_wrong_side(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    response = await client.post(
        "/api/v1/trades",
        json=_base_payload(suffix, criteria, direction="long", entry_price=100.0, stop_loss=105.0),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_register_trade_rejects_result_without_exit_price(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    response = await client.post(
        "/api/v1/trades",
        json=_base_payload(suffix, criteria, result="tp"),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_register_trade_rejects_missing_catalog_reference(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    response = await client.post(
        "/api/v1/trades",
        json=_base_payload(suffix, criteria, strategy_id=str(uuid.uuid4())),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_register_trade_rejects_inactive_catalog_reference(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    catalog_response = await client.post(
        "/api/v1/catalogs",
        json={"kind": "strategy", "name": f"strategy-{suffix}"},
        headers=headers,
    )
    assert catalog_response.status_code == 201, catalog_response.text
    strategy_id = catalog_response.json()["id"]
    deactivate_response = await client.post(
        f"/api/v1/catalogs/{strategy_id}/deactivate", headers=headers
    )
    assert deactivate_response.status_code == 200, deactivate_response.text

    response = await client.post(
        "/api/v1/trades",
        json=_base_payload(suffix, criteria, strategy_id=strategy_id),
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_register_trade_accepts_active_catalog_reference(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    catalog_response = await client.post(
        "/api/v1/catalogs",
        json={"kind": "strategy", "name": f"strategy-active-{suffix}"},
        headers=headers,
    )
    strategy_id = catalog_response.json()["id"]

    response = await client.post(
        "/api/v1/trades",
        json=_base_payload(suffix, criteria, strategy_id=strategy_id),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["strategy_id"] == strategy_id


async def test_register_trade_requires_authentication(client):
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
        },
    )
    assert response.status_code == 401


async def test_register_trade_idempotency_key_replays_stored_response_without_duplicating(
    client, db_session
):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    idempotency_headers = {**headers, "Idempotency-Key": f"key-{suffix}"}
    payload = _base_payload(suffix, criteria)

    first = await client.post("/api/v1/trades", json=payload, headers=idempotency_headers)
    assert first.status_code == 201, first.text
    second = await client.post("/api/v1/trades", json=payload, headers=idempotency_headers)
    assert second.status_code == 201, second.text

    assert first.json()["id"] == second.json()["id"]

    trade_id = uuid.UUID(first.json()["id"])
    trades_result = await db_session.execute(select(TradeModel).where(TradeModel.id == trade_id))
    assert len(trades_result.scalars().all()) == 1
