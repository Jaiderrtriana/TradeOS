"""
Integration tests: `POST/GET /journal-entries`, `GET/PATCH/DELETE
/journal-entries/{id}` (`TRADEOS_API_SPECIFICATION.md` §6.11, Sprint 5.1)
— run through the real FastAPI app, same client/auth fixture pattern as
tests/trading/test_trade_lifecycle_flow.py.
"""

import uuid
from datetime import date, timedelta

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
    email = f"journal-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _register_trade(client, headers) -> str:
    """A minimal Trade -- Journal never touches Evaluation, so no
    scoring criterion is needed, unlike tests that assert on computed
    scores. `RegisterTrade` still requires *some* published Configuration
    version to evaluate against (even with zero criteria/weights), so
    this creates and publishes an otherwise-empty one first."""
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

    payload = {
        "market": "EURUSD",
        "direction": "long",
        "status": "open",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "entered_at": "2026-01-01T00:00:00Z",
        "scoring_profile": PROFILE,
    }
    response = await client.post("/api/v1/trades", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ---------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------


async def test_create_trade_scoped_entry_succeeds(client):
    headers = await _auth_headers(client)
    trade_id = await _register_trade(client, headers)

    response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "Waited for confirmation before entering.", "trade_id": trade_id},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trade_id"] == trade_id
    assert body["period_start"] is None
    assert body["period_end"] is None
    assert body["content"] == "Waited for confirmation before entering."
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


async def test_create_period_scoped_entry_succeeds(client):
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/journal-entries",
        json={
            "content": "Weekly review: overtraded on Tuesday.",
            "period_start": "2026-07-20",
            "period_end": "2026-07-26",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["trade_id"] is None
    assert body["period_start"] == "2026-07-20"
    assert body["period_end"] == "2026-07-26"


async def test_create_rejects_both_reference_types(client):
    headers = await _auth_headers(client)
    trade_id = await _register_trade(client, headers)

    response = await client.post(
        "/api/v1/journal-entries",
        json={
            "content": "x",
            "trade_id": trade_id,
            "period_start": "2026-07-20",
            "period_end": "2026-07-26",
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_create_rejects_neither_reference_type(client):
    headers = await _auth_headers(client)

    response = await client.post("/api/v1/journal-entries", json={"content": "x"}, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_create_rejects_incomplete_period(client):
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-20"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_create_rejects_missing_trade(client):
    headers = await _auth_headers(client)

    response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "trade_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 404


async def test_create_rejects_not_owned_trade(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    trade_id = await _register_trade(client, headers_a)

    response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "trade_id": trade_id},
        headers=headers_b,
    )
    assert response.status_code == 404


async def test_create_requires_authentication(client):
    response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-20", "period_end": "2026-07-26"},
    )
    assert response.status_code == 401


async def test_create_is_idempotent_with_the_same_key(client):
    headers = await _auth_headers(client)
    idempotency_headers = {**headers, "Idempotency-Key": str(uuid.uuid4())}
    payload = {"content": "x", "period_start": "2026-07-20", "period_end": "2026-07-26"}

    first = await client.post("/api/v1/journal-entries", json=payload, headers=idempotency_headers)
    second = await client.post("/api/v1/journal-entries", json=payload, headers=idempotency_headers)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    list_response = await client.get("/api/v1/journal-entries", headers=headers)
    assert len(list_response.json()["data"]) == 1


# ---------------------------------------------------------------------
# List
# ---------------------------------------------------------------------


async def test_list_is_empty_for_a_fresh_user(client):
    headers = await _auth_headers(client)
    response = await client.get("/api/v1/journal-entries", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"data": [], "pagination": {"next_cursor": None, "has_more": False}}


async def test_list_returns_both_reference_types_newest_first(client):
    headers = await _auth_headers(client)
    trade_id = await _register_trade(client, headers)

    first = await client.post(
        "/api/v1/journal-entries",
        json={"content": "period entry", "period_start": "2026-07-20", "period_end": "2026-07-26"},
        headers=headers,
    )
    second = await client.post(
        "/api/v1/journal-entries",
        json={"content": "trade entry", "trade_id": trade_id},
        headers=headers,
    )
    assert first.status_code == 201 and second.status_code == 201

    response = await client.get("/api/v1/journal-entries", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [entry["id"] for entry in body["data"]] == [second.json()["id"], first.json()["id"]]


async def test_list_filters_by_trade_id(client):
    headers = await _auth_headers(client)
    trade_id = await _register_trade(client, headers)
    other_trade_id = await _register_trade(client, headers)

    await client.post(
        "/api/v1/journal-entries", json={"content": "a", "trade_id": trade_id}, headers=headers
    )
    await client.post(
        "/api/v1/journal-entries",
        json={"content": "b", "trade_id": other_trade_id},
        headers=headers,
    )

    response = await client.get(
        "/api/v1/journal-entries", params={"trade_id": trade_id}, headers=headers
    )
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["trade_id"] == trade_id


async def test_list_filters_by_period_overlap(client):
    headers = await _auth_headers(client)
    await client.post(
        "/api/v1/journal-entries",
        json={"content": "july", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers,
    )
    await client.post(
        "/api/v1/journal-entries",
        json={"content": "august", "period_start": "2026-08-01", "period_end": "2026-08-07"},
        headers=headers,
    )

    response = await client.get(
        "/api/v1/journal-entries",
        params={"period_start": "2026-07-01", "period_end": "2026-07-31"},
        headers=headers,
    )
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["content"] == "july"


async def test_list_ownership_scoping(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    await client.post(
        "/api/v1/journal-entries",
        json={"content": "a's entry", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers_a,
    )

    response = await client.get("/api/v1/journal-entries", headers=headers_b)
    assert response.json()["data"] == []


async def test_list_cursor_pagination_across_two_pages(client):
    headers = await _auth_headers(client)
    for day in range(3):
        start = date(2026, 7, 1) + timedelta(days=day)
        response = await client.post(
            "/api/v1/journal-entries",
            json={
                "content": f"entry {day}",
                "period_start": start.isoformat(),
                "period_end": start.isoformat(),
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text

    first_page = await client.get("/api/v1/journal-entries", params={"limit": 2}, headers=headers)
    first_body = first_page.json()
    assert len(first_body["data"]) == 2
    assert first_body["pagination"]["has_more"] is True
    cursor = first_body["pagination"]["next_cursor"]
    assert cursor is not None

    second_page = await client.get(
        "/api/v1/journal-entries", params={"limit": 2, "cursor": cursor}, headers=headers
    )
    second_body = second_page.json()
    assert len(second_body["data"]) == 1
    assert second_body["pagination"]["has_more"] is False

    first_ids = {entry["id"] for entry in first_body["data"]}
    second_ids = {entry["id"] for entry in second_body["data"]}
    assert first_ids.isdisjoint(second_ids)


async def test_list_requires_authentication(client):
    response = await client.get("/api/v1/journal-entries")
    assert response.status_code == 401


async def test_list_rejects_unsupported_sort(client):
    headers = await _auth_headers(client)
    response = await client.get(
        "/api/v1/journal-entries", params={"sort": "content"}, headers=headers
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------
# Get single
# ---------------------------------------------------------------------


async def test_get_single_entry_succeeds(client):
    headers = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers,
    )
    entry_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/journal-entries/{entry_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == entry_id


async def test_get_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.get(f"/api/v1/journal-entries/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_get_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers_a,
    )
    entry_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/journal-entries/{entry_id}", headers=headers_b)
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------


async def test_update_content_succeeds(client):
    headers = await _auth_headers(client)
    trade_id = await _register_trade(client, headers)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "original", "trade_id": trade_id},
        headers=headers,
    )
    entry_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/journal-entries/{entry_id}", json={"content": "edited"}, headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content"] == "edited"
    # The reference type/target is immutable after creation.
    assert body["trade_id"] == trade_id


async def test_update_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.patch(
        f"/api/v1/journal-entries/{uuid.uuid4()}", json={"content": "x"}, headers=headers
    )
    assert response.status_code == 404


async def test_update_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers_a,
    )
    entry_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/journal-entries/{entry_id}", json={"content": "hijacked"}, headers=headers_b
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------


async def test_delete_succeeds_and_is_then_not_found(client):
    headers = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers,
    )
    entry_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/journal-entries/{entry_id}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/journal-entries/{entry_id}", headers=headers)
    assert get_response.status_code == 404


async def test_delete_is_idempotent(client):
    headers = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers,
    )
    entry_id = create_response.json()["id"]

    first = await client.delete(f"/api/v1/journal-entries/{entry_id}", headers=headers)
    second = await client.delete(f"/api/v1/journal-entries/{entry_id}", headers=headers)
    assert first.status_code == 204
    assert second.status_code == 204


async def test_delete_not_found_returns_404(client):
    headers = await _auth_headers(client)
    response = await client.delete(f"/api/v1/journal-entries/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_delete_not_owned_returns_404(client):
    headers_a = await _auth_headers(client)
    headers_b = await _auth_headers(client)
    create_response = await client.post(
        "/api/v1/journal-entries",
        json={"content": "x", "period_start": "2026-07-01", "period_end": "2026-07-07"},
        headers=headers_a,
    )
    entry_id = create_response.json()["id"]

    response = await client.delete(f"/api/v1/journal-entries/{entry_id}", headers=headers_b)
    assert response.status_code == 404


async def test_delete_requires_authentication(client):
    response = await client.delete(f"/api/v1/journal-entries/{uuid.uuid4()}")
    assert response.status_code == 401
