"""
Integration tests: `PATCH /trades/{id}`, `POST /trades/{id}/close`,
`POST /trades/{id}/reevaluate`, `DELETE /trades/{id}`
(`TRADEOS_API_SPECIFICATION.md` §6.4, Sprint 4.2) — run through the real
FastAPI app, same client/auth fixture pattern as
tests/trading/test_register_trade_flow.py (Sprint 4.1).
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
    email = f"lifecycle-{uuid.uuid4()}@example.com"
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


async def _create_and_publish_version(
    client,
    headers,
    suffix: str,
    *,
    weight: float = 1.0,
    criteria: dict[str, tuple[str, str]] | None = None,
):
    """If `criteria` is omitted, a fresh set is created under `suffix`. If
    supplied (e.g. the same criteria an earlier version already used),
    this publishes a *new* version referencing those same criterion ids
    -- criteria are global, shared across every configuration version;
    only weights are per-version (`TRADEOS_DATABASE_DESIGN.md` §6.5)."""
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
            json={"criterion_id": criterion_id, "profile_code": PROFILE, "weight": weight},
            headers=headers,
        )
        assert weight_response.status_code == 200, weight_response.text

    publish_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert publish_response.status_code == 200, publish_response.text
    return version_id, criteria


def _base_payload(criteria: dict[str, tuple[str, str]], **overrides) -> dict:
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


# --- PATCH /trades/{id} (AmendTrade) -------------------------------------


async def test_amend_trade_updates_facts_and_recomputes_properties(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(
        client, headers, criteria, exit_price=108.0, result="tp", mfe_price=110.0, mae_price=97.0
    )

    response = await client.patch(
        f"/api/v1/trades/{trade['id']}", json={"entry_price": 120.0}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entry_price"] == 120.0
    # r_multiple recomputed from the new entry_price, proving the amend
    # actually persisted, not just echoed the request.
    assert body["r_multiple"] != trade["r_multiple"]
    assert body["evaluation"]["confidence"]["score"] == trade["evaluation"]["confidence"]["score"]


async def test_amend_trade_revalidates_full_merged_state_inv_trade_01(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    # direction stays "long"; moving stop_loss above entry_price alone
    # breaks INV-TRADE-01 against the *merged* state.
    response = await client.patch(
        f"/api/v1/trades/{trade['id']}", json={"stop_loss": 105.0}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_amend_trade_ignores_result_and_exit_price_fields(client):
    """result/exit_price/closed_at are not part of AmendTradeRequest's
    schema at all -- sending them is silently ignored (Pydantic's default
    extra-field behavior), never applied. CloseTrade is the only path
    that can transition result (API Specification §3.5)."""
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    response = await client.patch(
        f"/api/v1/trades/{trade['id']}",
        json={"result": "tp", "exit_price": 999.0},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "open"
    assert body["exit_price"] is None


async def test_amend_trade_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.patch(
        f"/api/v1/trades/{uuid.uuid4()}", json={"notes": "x"}, headers=headers
    )
    assert response.status_code == 404


async def test_amend_trade_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers_a, suffix)
    trade = await _register_trade(client, headers_a, criteria)

    response = await client.patch(
        f"/api/v1/trades/{trade['id']}", json={"notes": "hijacked"}, headers=headers_b
    )
    assert response.status_code == 404


async def test_amend_trade_requires_authentication(client):
    response = await client.patch(f"/api/v1/trades/{uuid.uuid4()}", json={"notes": "x"})
    assert response.status_code == 401


# --- POST /trades/{id}/close (CloseTrade) --------------------------------


async def test_close_trade_success(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)
    assert trade["result"] == "open"
    assert trade["closed_at"] is None

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/close",
        json={"result": "tp", "exit_price": 108.0, "mfe_price": 110.0, "mae_price": 97.0},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "tp"
    assert body["closed_at"] is not None
    assert body["r_multiple"] == 1.6
    assert body["captured_pct"] == 0.8


async def test_close_trade_preserves_existing_mfe_mae_when_omitted(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria, mfe_price=110.0, mae_price=97.0)

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/close",
        json={"result": "tp", "exit_price": 108.0},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mfe_price"] == 110.0
    assert body["mae_price"] == 97.0


async def test_close_trade_already_closed_returns_409(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)
    first = await client.post(
        f"/api/v1/trades/{trade['id']}/close",
        json={"result": "tp", "exit_price": 108.0},
        headers=headers,
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/api/v1/trades/{trade['id']}/close",
        json={"result": "sl", "exit_price": 90.0},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


async def test_close_trade_missing_exit_price_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/close", json={"result": "tp"}, headers=headers
    )
    # Pydantic-level 422 (exit_price is a required field of CloseTradeRequest).
    assert response.status_code == 422


# --- POST /trades/{id}/reevaluate (ReevaluateTrade) ----------------------


async def test_reevaluate_trade_produces_new_current_snapshot_and_supersedes_old(
    client, db_session
):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _v1_id, criteria = await _create_and_publish_version(client, headers, suffix, weight=1.0)
    trade = await _register_trade(client, headers, criteria)
    assert trade["evaluation"]["confidence"]["score"] == 100

    # A second published version reusing the *same* criteria (criteria are
    # global, shared across versions -- only weights are per-version) --
    # then the confidence criterion's own category_map is edited so "Yes"
    # now scores 0 instead of 100. The original ChecklistSnapshot answer
    # (keyed by source_field) is reused unchanged; only the criterion's
    # definition and the configuration version differ.
    v2_suffix = f"{suffix}-v2"
    v2_id, _v2_criteria = await _create_and_publish_version(
        client, headers, v2_suffix, weight=1.0, criteria=criteria
    )
    await client.patch(
        f"/api/v1/configuration/scoring-criteria/{criteria['confidence'][0]}",
        json={"category_map": {"Yes": 0, "No": 100}},
        headers=headers,
    )

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/reevaluate",
        json={"scoring_profile": PROFILE, "configuration_version_id": v2_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # Response is the EvaluationSnapshot shape only -- no "id"/Trade wrapper.
    assert set(body.keys()) == {"confidence", "quality", "execution", "market_context", "bias"}
    assert body["confidence"]["score"] == 0

    trade_id = uuid.UUID(trade["id"])
    snapshots_result = await db_session.execute(
        select(EvaluationSnapshotModel)
        .where(EvaluationSnapshotModel.trade_id == trade_id)
        .order_by(EvaluationSnapshotModel.created_at)
    )
    snapshots = snapshots_result.scalars().all()
    assert len(snapshots) == 2
    assert snapshots[0].is_current is False
    assert snapshots[0].configuration_version_id == uuid.UUID(_v1_id)
    assert snapshots[1].is_current is True
    assert snapshots[1].configuration_version_id == uuid.UUID(v2_id)


async def test_reevaluate_trade_rejects_draft_configuration_version(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    draft_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-draft-{suffix}"},
        headers=headers,
    )
    assert draft_response.status_code == 201, draft_response.text
    draft_id = draft_response.json()["id"]

    response = await client.post(
        f"/api/v1/trades/{trade['id']}/reevaluate",
        json={"scoring_profile": PROFILE, "configuration_version_id": draft_id},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_reevaluate_trade_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/trades/{uuid.uuid4()}/reevaluate",
        json={"scoring_profile": PROFILE},
        headers=headers,
    )
    assert response.status_code == 404


# --- DELETE /trades/{id} (DeleteTrade) ------------------------------------


async def test_delete_trade_soft_deletes_and_is_idempotent(client, db_session):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)
    trade_id = uuid.UUID(trade["id"])

    first = await client.delete(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert first.status_code == 204

    row = (
        await db_session.execute(select(TradeModel).where(TradeModel.id == trade_id))
    ).scalar_one()
    assert row.deleted_at is not None

    # DELETE is idempotent (API Specification §3.4) -- repeating it is a
    # successful no-op, never a 404.
    second = await client.delete(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert second.status_code == 204


async def test_amend_soft_deleted_trade_returns_404(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _create_and_publish_version(client, headers, suffix)
    trade = await _register_trade(client, headers, criteria)

    delete_response = await client.delete(f"/api/v1/trades/{trade['id']}", headers=headers)
    assert delete_response.status_code == 204

    response = await client.patch(
        f"/api/v1/trades/{trade['id']}", json={"notes": "too late"}, headers=headers
    )
    assert response.status_code == 404


async def test_delete_trade_requires_authentication(client):
    response = await client.delete(f"/api/v1/trades/{uuid.uuid4()}")
    assert response.status_code == 401
