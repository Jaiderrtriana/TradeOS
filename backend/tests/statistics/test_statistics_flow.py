"""
Integration tests: `GET /statistics/overview`, `GET /statistics/by-dimension`,
`GET /statistics/rolling` (`TRADEOS_API_SPECIFICATION.md` §6.10, Sprints
6.1-6.2) — run through the real FastAPI app, same client/auth fixture
pattern as tests/mistakes/test_mistake_ranking_flow.py.

Formulas under test (approved, Sprint 6.1 pre-analysis — no document
defines these precisely): Win Rate = count(TP) / count(closed);
Expectancy = Average R = mean(r_multiple) over closed trades;
Profit Factor = gross_profit_r / gross_loss_r (None if no losses);
Total P&L = sum(realized_pnl) over all non-deleted trades; by-dimension
buckets a null strategy/setup/session as "unassigned". Rolling (approved,
Sprint 6.2 pre-analysis): the window is drawn from the most recent N
Trades by `entered_at` across the *entire* non-deleted set, then
`aggregate_statistics` runs unchanged over that subset (`rolling`) and
over the full set (`overall`).
"""

import uuid
from datetime import datetime, timezone

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
    email = f"statistics-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _publish_empty_configuration_version(client, headers) -> None:
    """`RegisterTrade` requires some published Configuration version to
    evaluate against, even with zero criteria/weights."""
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


async def _publish_confidence_criterion(client, headers, suffix: str) -> str:
    """Creates one `confidence` criterion, weights it into a new version,
    and publishes it -- returns the criterion's `source_field`, so a
    caller can supply a real `checklist_answers` value and get a
    non-`None` `confidence_score` back."""
    criterion_payload = {
        "id": f"confidence.{suffix}",
        "engine_type_code": "confidence",
        "name": f"Confidence {suffix}",
        "source_field": f"confidence_{suffix}_field",
        "min_value": 0,
        "max_value": 100,
        "category_map": {"Yes": 100, "No": 0},
    }
    criterion_response = await client.post(
        "/api/v1/configuration/scoring-criteria", json=criterion_payload, headers=headers
    )
    assert criterion_response.status_code == 201, criterion_response.text

    version_response = await client.post(
        "/api/v1/configuration/versions", json={"version_label": f"v-{suffix}"}, headers=headers
    )
    version_id = version_response.json()["id"]
    weight_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/weights",
        json={"criterion_id": criterion_payload["id"], "profile_code": PROFILE, "weight": 1.0},
        headers=headers,
    )
    assert weight_response.status_code == 200, weight_response.text
    publish_response = await client.post(
        f"/api/v1/configuration/versions/{version_id}/publish", headers=headers
    )
    assert publish_response.status_code == 200, publish_response.text
    return criterion_payload["source_field"]


async def _register_trade(
    client,
    headers,
    *,
    entry_price: float = 100.0,
    stop_loss: float = 95.0,
    strategy_id: str | None = None,
    checklist_answers: dict | None = None,
) -> str:
    payload = {
        "market": "EURUSD",
        "direction": "long",
        "status": "open",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        # Client-supplied now (v2.0 -- the server no longer defaults it):
        # a fresh timestamp per call, same "each registration is later
        # than the last" ordering the old server-side `now()` default
        # gave the Rolling Statistics tests below for free.
        "entered_at": datetime.now(timezone.utc).isoformat(),
        "scoring_profile": PROFILE,
    }
    if strategy_id is not None:
        payload["strategy_id"] = strategy_id
    if checklist_answers is not None:
        payload["checklist_answers"] = checklist_answers
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
            "closed_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


async def _create_catalog_entry(client, headers, *, kind: str, name: str) -> str:
    response = await client.post(
        "/api/v1/catalogs", json={"kind": kind, "name": name}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ---------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------


async def test_overview_is_all_none_for_a_fresh_user(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/statistics/overview", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["win_rate"] is None
    assert body["expectancy_r"] is None
    assert body["average_r"] is None
    assert body["profit_factor_r"] is None
    assert body["total_pnl"] == 0
    assert body["average_confidence_score"] is None


async def test_overview_computes_win_rate_expectancy_average_r_and_profit_factor(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    # Long, entry 100 / stop 95 (risk = 5).
    tp_trade = await _register_trade(client, headers)
    await _close_trade(client, headers, tp_trade, result="tp", exit_price=110.0)  # r = +2.0

    sl_trade = await _register_trade(client, headers)
    await _close_trade(client, headers, sl_trade, result="sl", exit_price=95.0)  # r = -1.0

    be_trade = await _register_trade(client, headers)
    await _close_trade(client, headers, be_trade, result="be", exit_price=100.0)  # r = 0.0

    open_trade = await _register_trade(
        client, headers
    )  # never closed -- must be excluded from R metrics
    assert open_trade

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    body = response.json()

    # Win Rate: 1 TP out of 3 *closed* trades (TP, SL, BE) -- the open
    # trade is excluded from the denominator entirely.
    assert body["win_rate"] == 1 / 3

    # Expectancy == Average R == mean([2.0, -1.0, 0.0]).
    expected_mean_r = (2.0 + -1.0 + 0.0) / 3
    assert body["expectancy_r"] == expected_mean_r
    assert body["average_r"] == expected_mean_r

    # Profit Factor: gross_profit_r=2.0, gross_loss_r=1.0 (BE's 0.0 is
    # neither profit nor loss).
    assert body["profit_factor_r"] == 2.0


async def test_overview_profit_factor_is_none_with_no_losses(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    trade = await _register_trade(client, headers)
    await _close_trade(client, headers, trade, result="tp", exit_price=110.0)

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    body = response.json()
    assert body["profit_factor_r"] is None


async def test_overview_total_pnl_sums_realized_pnl_across_all_non_deleted_trades(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    await _register_trade(client, headers)
    trade = await _register_trade(client, headers)
    await _close_trade(client, headers, trade, result="tp", exit_price=110.0)

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    body = response.json()
    # No endpoint sets `realized_pnl` to a nonzero value anywhere in this
    # codebase today -- it stays at its schema default (0) for every
    # Trade, so the honest, correct sum here is 0.
    assert body["total_pnl"] == 0


async def test_overview_averages_engine_scores_skipping_none(client):
    headers = await _auth_headers(client)
    confidence_field = await _publish_confidence_criterion(client, headers, uuid.uuid4().hex[:8])

    trade_a = await _register_trade(client, headers, checklist_answers={confidence_field: "Yes"})
    await _close_trade(client, headers, trade_a, result="tp", exit_price=110.0)

    trade_b = await _register_trade(client, headers, checklist_answers={confidence_field: "No"})
    await _close_trade(client, headers, trade_b, result="sl", exit_price=95.0)

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    body = response.json()
    # category_map {"Yes": 100, "No": 0}, one criterion, weight 1.0 --
    # confidence_score is 100 and 0 respectively; mean = 50.
    assert body["average_confidence_score"] == 50.0
    # The other four engines have zero criteria configured, but each
    # still legitimately computes a real score of 0 (a weighted sum over
    # zero criteria is 0, not "not computable") -- confirmed against
    # `score_quality`'s own signature, which always returns a `Score`,
    # never `None`. The `None`-skipping path this aggregation also
    # implements (for a genuinely absent score, e.g. a future sixth
    # engine on a historical snapshot) is covered directly at the domain
    # layer instead, in test_statistics_aggregation.py -- today's system
    # never actually produces a `None` engine score to exercise here.
    assert body["average_quality_score"] == 0.0


async def test_overview_requires_authentication(client):
    response = await client.get("/api/v1/statistics/overview")
    assert response.status_code == 401


async def test_overview_is_scoped_to_the_requesting_user(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers_a)

    trade = await _register_trade(client, headers_a)
    await _close_trade(client, headers_a, trade, result="tp", exit_price=110.0)

    response = await client.get("/api/v1/statistics/overview", headers=headers_b)
    body = response.json()
    assert body["win_rate"] is None
    assert body["total_pnl"] == 0


# ---------------------------------------------------------------------
# By dimension
# ---------------------------------------------------------------------


async def test_by_dimension_direction_groups_without_a_catalog_lookup(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    trade = await _register_trade(client, headers)
    await _close_trade(client, headers, trade, result="tp", exit_price=110.0)

    response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "direction"}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["dimension_value"] == "long"
    assert body[0]["label"] == "long"
    assert body[0]["win_rate"] == 1.0


async def test_by_dimension_strategy_resolves_catalog_names(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    strategy_id = await _create_catalog_entry(
        client, headers, kind="strategy", name=f"Breakout-{uuid.uuid4().hex[:8]}"
    )

    trade = await _register_trade(client, headers, strategy_id=strategy_id)
    await _close_trade(client, headers, trade, result="tp", exit_price=110.0)

    response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "strategy"}, headers=headers
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["dimension_value"] == strategy_id
    assert body[0]["label"].startswith("Breakout-")


async def test_by_dimension_buckets_unassigned_strategy_explicitly(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    trade = await _register_trade(client, headers)  # no strategy_id
    await _close_trade(client, headers, trade, result="tp", exit_price=110.0)

    response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "strategy"}, headers=headers
    )
    body = response.json()
    assert len(body) == 1
    assert body[0]["dimension_value"] == "unassigned"
    assert body[0]["label"] == "Unassigned"
    assert body[0]["win_rate"] == 1.0


async def test_by_dimension_rejects_an_unsupported_dimension(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "entry_trigger"}, headers=headers
    )
    assert response.status_code == 422


async def test_by_dimension_requires_authentication(client):
    response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "direction"}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------
# Exit Criteria (Master Plan Sprint 6.1): a hand-computed Win Rate/
# Expectancy over the same Trade set matches the endpoint's output
# exactly.
# ---------------------------------------------------------------------


async def test_exit_criteria_hand_computed_win_rate_and_expectancy_match_exactly(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    # A small, fully controlled trade set -- every r_multiple computed
    # by hand from entry=100/stop=95 (risk=5).
    closes = [
        ("tp", 115.0),  # r = +3.0
        ("tp", 110.0),  # r = +2.0
        ("sl", 90.0),  # r = -2.0 (below stop, still a valid SL close)
        ("sl", 95.0),  # r = -1.0
        ("be", 100.0),  # r =  0.0
    ]
    for result, exit_price in closes:
        trade_id = await _register_trade(client, headers)
        await _close_trade(client, headers, trade_id, result=result, exit_price=exit_price)

    # Hand computation, independent of the implementation:
    r_values = [3.0, 2.0, -2.0, -1.0, 0.0]
    hand_win_rate = 2 / 5  # 2 TP out of 5 closed trades
    hand_expectancy = sum(r_values) / len(r_values)

    response = await client.get("/api/v1/statistics/overview", headers=headers)
    body = response.json()
    assert body["win_rate"] == hand_win_rate
    assert body["expectancy_r"] == hand_expectancy
    assert body["average_r"] == hand_expectancy


# ---------------------------------------------------------------------
# Rolling (Sprint 6.2)
# ---------------------------------------------------------------------


async def test_rolling_rejects_an_unsupported_window(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/statistics/rolling", params={"window": 15}, headers=headers
    )
    assert response.status_code == 422


async def test_rolling_requires_authentication(client):
    response = await client.get("/api/v1/statistics/rolling", params={"window": 10})
    assert response.status_code == 401


async def test_rolling_is_scoped_to_the_requesting_user(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers_a)

    trade = await _register_trade(client, headers_a)
    await _close_trade(client, headers_a, trade, result="tp", exit_price=110.0)

    response = await client.get(
        "/api/v1/statistics/rolling", params={"window": 10}, headers=headers_b
    )
    body = response.json()
    assert body["window"] == 10
    assert body["rolling"]["win_rate"] is None
    assert body["overall"]["win_rate"] is None


async def test_rolling_with_fewer_trades_than_window_equals_overall(client):
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    tp_trade = await _register_trade(client, headers)
    await _close_trade(client, headers, tp_trade, result="tp", exit_price=110.0)
    sl_trade = await _register_trade(client, headers)
    await _close_trade(client, headers, sl_trade, result="sl", exit_price=95.0)

    response = await client.get(
        "/api/v1/statistics/rolling", params={"window": 10}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["window"] == 10
    assert body["rolling"] == body["overall"]


async def test_exit_criteria_rolling_window_only_reflects_the_most_recent_n_trades(client):
    """Master Plan Milestone M6: "Rolling tabs... return figures that are
    independently verifiable by hand-computing them from the same
    underlying Trades" (DI-11). Registers 2 older SL trades followed by
    10 newer TP trades (`window=10`, the smallest value the endpoint
    accepts) -- `rolling` must reflect only the 10 TP trades, `overall`
    must reflect all 12, hand-computed independently of the
    implementation."""
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)

    for _ in range(2):
        trade_id = await _register_trade(client, headers)
        await _close_trade(client, headers, trade_id, result="sl", exit_price=95.0)  # r = -1.0

    for _ in range(10):
        trade_id = await _register_trade(client, headers)
        await _close_trade(client, headers, trade_id, result="tp", exit_price=110.0)  # r = +2.0

    response = await client.get(
        "/api/v1/statistics/rolling", params={"window": 10}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["window"] == 10
    # Rolling: the 10 most recently registered trades are all the TP
    # trades registered last -- hand-computed win rate 1.0, expectancy 2.0.
    assert body["rolling"]["win_rate"] == 1.0
    assert body["rolling"]["expectancy_r"] == 2.0
    assert body["rolling"]["average_r"] == 2.0

    # Overall: all 12 trades -- hand-computed win rate 10/12, expectancy
    # mean([-1.0, -1.0] + [2.0] * 10).
    hand_overall_win_rate = 10 / 12
    hand_overall_expectancy = ((-1.0 * 2) + (2.0 * 10)) / 12
    assert body["overall"]["win_rate"] == hand_overall_win_rate
    assert body["overall"]["expectancy_r"] == hand_overall_expectancy
    assert body["overall"]["average_r"] == hand_overall_expectancy
