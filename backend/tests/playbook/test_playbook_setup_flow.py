"""
Integration tests: `POST/GET /playbook-setups`, `GET/PATCH
/playbook-setups/{id}`, `POST /playbook-setups/{id}/deprecate`,
`POST /playbook-setups/{id}/attachments`,
`DELETE /playbook-setups/{id}/attachments/{attachmentId}`
(`TRADEOS_API_SPECIFICATION.md` §6.8, Sprint 7.1) — run through the real
FastAPI app, same client/auth fixture pattern as
tests/statistics/test_statistics_flow.py.

`PlaybookSetup` is a global resource, never scoped by `user_id`
(`TRADEOS_API_SPECIFICATION.md` line 101, Sprint 7.1 pre-analysis) --
unlike every other resource-ownership test elsewhere in this suite, no
test here asserts per-user isolation of the setup itself. Its composed
`performance`, however, IS scoped by the calling user (Statistics'
existing behavior, unchanged) -- covered by the Exit Criteria test below.
"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.platform.db.models import EventLog
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
    email = f"playbook-{uuid.uuid4()}@example.com"
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


async def _create_catalog_entry(client, headers, *, kind: str, name: str) -> str:
    response = await client.post(
        "/api/v1/catalogs", json={"kind": kind, "name": name}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _register_trade(
    client,
    headers,
    *,
    setup_id: str | None = None,
    entry_price: float = 100.0,
    stop_loss: float = 95.0,
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
    if setup_id is not None:
        payload["setup_id"] = setup_id
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


# ---------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------


async def test_create_rejects_a_non_setup_catalog_entry(client):
    headers = await _auth_headers(client)
    session_id = await _create_catalog_entry(
        client, headers, kind="session", name=f"NY-{uuid.uuid4().hex[:8]}"
    )
    response = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": session_id}, headers=headers
    )
    assert response.status_code == 422


async def test_create_rejects_a_nonexistent_catalog_entry(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/playbook-setups",
        json={"catalog_entry_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_rejects_a_catalog_entry_already_linked(client):
    headers = await _auth_headers(client)
    setup_catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Breakout-{uuid.uuid4().hex[:8]}"
    )
    first = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": setup_catalog_id}, headers=headers
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": setup_catalog_id}, headers=headers
    )
    assert second.status_code == 422


async def test_create_with_only_the_required_field_defaults_text_fields_to_empty(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Pullback-{uuid.uuid4().hex[:8]}"
    )
    response = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["entry_criteria"] == ""
    assert body["exit_criteria"] == ""
    assert body["ideal_conditions"] == ""
    assert body["risk_rules"] == ""
    assert body["status"] == "active"


async def test_create_returns_the_name_from_the_linked_catalog_entry(client):
    headers = await _auth_headers(client)
    name = f"Breakout-{uuid.uuid4().hex[:8]}"
    catalog_id = await _create_catalog_entry(client, headers, kind="setup", name=name)
    response = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    assert response.json()["name"] == name


async def test_create_with_idempotency_key_returns_the_same_setup_on_retry(client):
    headers = {**await _auth_headers(client), "Idempotency-Key": str(uuid.uuid4())}
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Range-{uuid.uuid4().hex[:8]}"
    )

    first = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    second = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


async def test_create_requires_authentication(client):
    response = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": str(uuid.uuid4())}
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------
# List
# ---------------------------------------------------------------------


async def test_list_paginates_with_cursor(client):
    headers = await _auth_headers(client)
    for _ in range(3):
        catalog_id = await _create_catalog_entry(
            client, headers, kind="setup", name=f"S-{uuid.uuid4().hex[:8]}"
        )
        await client.post(
            "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
        )

    first_page = await client.get("/api/v1/playbook-setups", params={"limit": 2}, headers=headers)
    assert first_page.status_code == 200, first_page.text
    first_body = first_page.json()
    assert len(first_body["data"]) == 2
    assert first_body["pagination"]["has_more"] is True
    assert first_body["pagination"]["next_cursor"] is not None

    second_page = await client.get(
        "/api/v1/playbook-setups",
        params={"limit": 2, "cursor": first_body["pagination"]["next_cursor"]},
        headers=headers,
    )
    assert second_page.status_code == 200, second_page.text
    # At least the third setup created above -- may include setups from
    # other tests sharing the same ephemeral database, so only a lower
    # bound is asserted, never an exact count.
    assert len(second_page.json()["data"]) >= 1


async def test_list_rejects_an_unsupported_sort_field(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/playbook-setups", params={"sort": "name"}, headers=headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------
# Get (detail + performance composition)
# ---------------------------------------------------------------------


async def test_get_returns_404_for_a_missing_setup(client):
    headers = await _auth_headers(client)
    response = await client.get(f"/api/v1/playbook-setups/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_get_returns_all_none_performance_for_a_setup_with_no_trades(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Fresh-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    response = await client.get(f"/api/v1/playbook-setups/{setup_id}", headers=headers)
    assert response.status_code == 200, response.text
    performance = response.json()["performance"]
    assert performance["win_rate"] is None
    assert performance["total_pnl"] == 0


async def test_exit_criteria_performance_matches_statistics_by_dimension_exactly(client):
    """Master Plan Sprint 7.1 Exit Criteria (literal): "a Playbook Setup's
    performance figures match the equivalent Statistics by-dimension
    query for that same Setup, exactly." Verifies both sides key off the
    identical identifier: the setup's `catalog_entry_id` and the
    by-dimension response's `dimension_value` for `dimension=setup`."""
    headers = await _auth_headers(client)
    await _publish_empty_configuration_version(client, headers)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"ExitCriteria-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    tp_trade = await _register_trade(client, headers, setup_id=catalog_id)
    await _close_trade(client, headers, tp_trade, result="tp", exit_price=110.0)  # r = +2.0
    sl_trade = await _register_trade(client, headers, setup_id=catalog_id)
    await _close_trade(client, headers, sl_trade, result="sl", exit_price=95.0)  # r = -1.0

    detail_response = await client.get(f"/api/v1/playbook-setups/{setup_id}", headers=headers)
    assert detail_response.status_code == 200, detail_response.text
    detail_performance = detail_response.json()["performance"]

    by_dimension_response = await client.get(
        "/api/v1/statistics/by-dimension", params={"dimension": "setup"}, headers=headers
    )
    assert by_dimension_response.status_code == 200, by_dimension_response.text
    matching_group = next(
        g for g in by_dimension_response.json() if g["dimension_value"] == catalog_id
    )

    for field in (
        "win_rate",
        "expectancy_r",
        "average_r",
        "profit_factor_r",
        "total_pnl",
        "average_confidence_score",
        "average_quality_score",
        "average_execution_score",
        "average_market_context_score",
        "average_bias_score",
    ):
        assert detail_performance[field] == matching_group[field], field

    # Hand-computed, independent of either implementation.
    assert detail_performance["win_rate"] == 0.5
    assert detail_performance["expectancy_r"] == 0.5  # mean([2.0, -1.0])


async def test_get_includes_attachments(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"WithAttachment-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]
    await client.post(
        f"/api/v1/playbook-setups/{setup_id}/attachments",
        json={"file_reference": "https://example.com/chart.png", "caption": "Entry"},
        headers=headers,
    )

    response = await client.get(f"/api/v1/playbook-setups/{setup_id}", headers=headers)
    attachments = response.json()["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["file_reference"] == "https://example.com/chart.png"


# ---------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------


async def test_update_only_overwrites_supplied_fields(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Partial-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups",
        json={"catalog_entry_id": catalog_id, "entry_criteria": "Original entry"},
        headers=headers,
    )
    setup_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/playbook-setups/{setup_id}",
        json={"exit_criteria": "New exit"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["entry_criteria"] == "Original entry"
    assert body["exit_criteria"] == "New exit"


async def test_update_returns_404_for_a_missing_setup(client):
    headers = await _auth_headers(client)
    response = await client.patch(
        f"/api/v1/playbook-setups/{uuid.uuid4()}", json={"risk_rules": "x"}, headers=headers
    )
    assert response.status_code == 404


async def test_update_publishes_playbook_setup_updated(client, db_session):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"Eventful-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    await client.patch(
        f"/api/v1/playbook-setups/{setup_id}", json={"risk_rules": "Max 1% risk"}, headers=headers
    )

    result = await db_session.execute(
        select(EventLog).where(
            EventLog.event_type == "PlaybookSetupUpdated",
            EventLog.aggregate_id == uuid.UUID(setup_id),
        )
    )
    logged = result.scalar_one_or_none()
    assert logged is not None
    assert logged.aggregate_type == "PlaybookSetup"


# ---------------------------------------------------------------------
# Deprecate
# ---------------------------------------------------------------------


async def test_deprecate_changes_status_to_deprecated(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"ToDeprecate-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    response = await client.post(f"/api/v1/playbook-setups/{setup_id}/deprecate", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "deprecated"


async def test_deprecate_twice_returns_409(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"DoubleDeprecate-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]
    await client.post(f"/api/v1/playbook-setups/{setup_id}/deprecate", headers=headers)

    second = await client.post(f"/api/v1/playbook-setups/{setup_id}/deprecate", headers=headers)
    assert second.status_code == 409


async def test_deprecate_does_not_affect_the_linked_catalog_entrys_active_status(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"NoCascade-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    await client.post(f"/api/v1/playbook-setups/{setup_id}/deprecate", headers=headers)

    catalog_response = await client.get(
        "/api/v1/catalogs", params={"kind": "setup"}, headers=headers
    )
    # `GET /catalogs` is a bare list, not a pagination envelope.
    entry = next(e for e in catalog_response.json() if e["id"] == catalog_id)
    assert entry["is_active"] is True


async def test_deprecate_returns_404_for_a_missing_setup(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/playbook-setups/{uuid.uuid4()}/deprecate", headers=headers
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------


async def test_add_attachment_returns_201(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"AttachOK-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/playbook-setups/{setup_id}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["caption"] == ""


async def test_add_attachment_returns_404_for_a_missing_setup(client):
    headers = await _auth_headers(client)
    response = await client.post(
        f"/api/v1/playbook-setups/{uuid.uuid4()}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=headers,
    )
    assert response.status_code == 404


async def test_add_attachment_with_idempotency_key_does_not_duplicate(client):
    # A *different* Idempotency-Key from the one used for setup creation
    # below -- claims are keyed only by `(user_id, key)`, never by
    # endpoint, so reusing one key across two different creations would
    # make the second short-circuit to the first's stored response.
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"AttachIdem-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]

    attachment_headers = {**headers, "Idempotency-Key": str(uuid.uuid4())}
    first = await client.post(
        f"/api/v1/playbook-setups/{setup_id}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=attachment_headers,
    )
    second = await client.post(
        f"/api/v1/playbook-setups/{setup_id}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=attachment_headers,
    )
    assert first.json()["id"] == second.json()["id"]

    detail = await client.get(f"/api/v1/playbook-setups/{setup_id}", headers=headers)
    assert len(detail.json()["attachments"]) == 1


async def test_delete_attachment_returns_204_and_removes_it(client):
    headers = await _auth_headers(client)
    catalog_id = await _create_catalog_entry(
        client, headers, kind="setup", name=f"AttachDelete-{uuid.uuid4().hex[:8]}"
    )
    created = await client.post(
        "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id}, headers=headers
    )
    setup_id = created.json()["id"]
    attachment = await client.post(
        f"/api/v1/playbook-setups/{setup_id}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=headers,
    )
    attachment_id = attachment.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/playbook-setups/{setup_id}/attachments/{attachment_id}", headers=headers
    )
    assert delete_response.status_code == 204

    detail = await client.get(f"/api/v1/playbook-setups/{setup_id}", headers=headers)
    assert detail.json()["attachments"] == []


async def test_delete_attachment_returns_404_when_it_belongs_to_a_different_setup(client):
    headers = await _auth_headers(client)
    catalog_id_a = await _create_catalog_entry(
        client, headers, kind="setup", name=f"OwnerA-{uuid.uuid4().hex[:8]}"
    )
    catalog_id_b = await _create_catalog_entry(
        client, headers, kind="setup", name=f"OwnerB-{uuid.uuid4().hex[:8]}"
    )
    setup_a = (
        await client.post(
            "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id_a}, headers=headers
        )
    ).json()["id"]
    setup_b = (
        await client.post(
            "/api/v1/playbook-setups", json={"catalog_entry_id": catalog_id_b}, headers=headers
        )
    ).json()["id"]
    attachment = await client.post(
        f"/api/v1/playbook-setups/{setup_a}/attachments",
        json={"file_reference": "https://example.com/a.png"},
        headers=headers,
    )
    attachment_id = attachment.json()["id"]

    response = await client.delete(
        f"/api/v1/playbook-setups/{setup_b}/attachments/{attachment_id}", headers=headers
    )
    assert response.status_code == 404
