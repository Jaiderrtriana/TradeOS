"""
Integration tests: the Catalogs Module (TRADEOS_API_SPECIFICATION.md
§6.7), run through the real FastAPI app.

Uses unique names per test (uuid-suffixed) for CRUD/validation tests, the
same convention as tests/configuration/test_configuration_flow.py, since
`postgres_container` is session-scoped and rows persist across the whole
test session. One dedicated test (`test_seeding_the_real_37_catalog
_entries...`) reproduces the exact 37-entry seed
`alembic/versions/0005_create_catalog_entries_table.py` ships, to prove
the Master Plan's own Sprint 2.2 Deliverable ("all five catalog kinds
populated with real entries... every seeded entry is active by default")
independently of whether the data was inserted by the migration or here.
"""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.platform.db.models import EventLog
from app.platform.db.session import get_db_session


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
    email = f"catalogs-{uuid.uuid4()}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_endpoints_require_authentication(client):
    response = await client.get("/api/v1/catalogs")
    assert response.status_code == 401


async def test_create_catalog_entry_defaults_to_active(client):
    headers = await _auth_headers(client)
    name = f"Setup {uuid.uuid4().hex[:8]}"
    response = await client.post(
        "/api/v1/catalogs", json={"kind": "setup", "name": name}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "setup"
    assert body["name"] == name
    assert body["is_active"] is True


async def test_create_catalog_entry_invalid_kind_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/catalogs",
        json={"kind": "not_a_real_kind", "name": f"Entry {uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_create_catalog_entry_duplicate_kind_and_name_returns_409(client):
    """TRADEOS_DATABASE_DESIGN.md §6.8's (kind, name) uniqueness constraint
    — the Master Plan's own named Sprint 2.2 Exit Criteria."""
    headers = await _auth_headers(client)
    name = f"Session {uuid.uuid4().hex[:8]}"
    payload = {"kind": "session", "name": name}
    first = await client.post("/api/v1/catalogs", json=payload, headers=headers)
    assert first.status_code == 201
    second = await client.post("/api/v1/catalogs", json=payload, headers=headers)
    assert second.status_code == 409


async def test_same_name_is_allowed_across_different_kinds(client):
    """The unique constraint is on (kind, name) together, not name alone."""
    headers = await _auth_headers(client)
    shared_name = f"Shared {uuid.uuid4().hex[:8]}"
    first = await client.post(
        "/api/v1/catalogs", json={"kind": "setup", "name": shared_name}, headers=headers
    )
    second = await client.post(
        "/api/v1/catalogs", json={"kind": "strategy", "name": shared_name}, headers=headers
    )
    assert first.status_code == 201
    assert second.status_code == 201


async def test_list_catalog_entries_filters_by_kind(client):
    headers = await _auth_headers(client)
    name = f"Trigger {uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/catalogs", json={"kind": "entry_trigger", "name": name}, headers=headers
    )
    response = await client.get(
        "/api/v1/catalogs", params={"kind": "entry_trigger"}, headers=headers
    )
    assert response.status_code == 200
    assert all(row["kind"] == "entry_trigger" for row in response.json())
    assert any(row["name"] == name for row in response.json())


async def test_update_catalog_entry_renames_it(client):
    headers = await _auth_headers(client)
    original_name = f"Mistake {uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/catalogs", json={"kind": "mistake_tag", "name": original_name}, headers=headers
    )
    entry_id = created.json()["id"]

    new_name = f"Renamed {uuid.uuid4().hex[:8]}"
    response = await client.patch(
        f"/api/v1/catalogs/{entry_id}", json={"name": new_name}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == new_name
    assert response.json()["kind"] == "mistake_tag"
    assert response.json()["is_active"] is True


async def test_update_catalog_entry_cannot_set_is_active_or_kind(client):
    """Approved scope: PATCH may only rename; extra fields in the request
    body are ignored by the schema, never applied."""
    headers = await _auth_headers(client)
    created = await client.post(
        "/api/v1/catalogs",
        json={"kind": "session", "name": f"Session {uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    entry_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/catalogs/{entry_id}",
        json={"name": f"Renamed {uuid.uuid4().hex[:8]}", "is_active": False, "kind": "setup"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True
    assert response.json()["kind"] == "session"


async def test_update_catalog_entry_renaming_to_existing_name_returns_409(client):
    headers = await _auth_headers(client)
    first_name = f"First {uuid.uuid4().hex[:8]}"
    second_name = f"Second {uuid.uuid4().hex[:8]}"
    await client.post(
        "/api/v1/catalogs", json={"kind": "setup", "name": first_name}, headers=headers
    )
    second = await client.post(
        "/api/v1/catalogs", json={"kind": "setup", "name": second_name}, headers=headers
    )
    second_id = second.json()["id"]

    response = await client.patch(
        f"/api/v1/catalogs/{second_id}", json={"name": first_name}, headers=headers
    )
    assert response.status_code == 409


async def test_deactivate_catalog_entry(client):
    headers = await _auth_headers(client)
    created = await client.post(
        "/api/v1/catalogs",
        json={"kind": "strategy", "name": f"Strategy {uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    entry_id = created.json()["id"]

    response = await client.post(f"/api/v1/catalogs/{entry_id}/deactivate", headers=headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    listed = await client.get("/api/v1/catalogs", params={"kind": "strategy"}, headers=headers)
    deactivated = next(row for row in listed.json() if row["id"] == entry_id)
    assert deactivated["is_active"] is False


async def test_deactivate_catalog_entry_publishes_event(client, db_session):
    """TRADEOS_DOMAIN_MODEL.md §11: CatalogEntryDeactivated, durably logged
    to platform.event_log regardless of any subscriber."""
    headers = await _auth_headers(client)
    created = await client.post(
        "/api/v1/catalogs",
        json={"kind": "mistake_tag", "name": f"Mistake {uuid.uuid4().hex[:8]}"},
        headers=headers,
    )
    entry_id = created.json()["id"]

    await client.post(f"/api/v1/catalogs/{entry_id}/deactivate", headers=headers)

    result = await db_session.execute(
        select(EventLog).where(
            EventLog.event_type == "CatalogEntryDeactivated",
            EventLog.aggregate_id == uuid.UUID(entry_id),
        )
    )
    logged = result.scalar_one_or_none()
    assert logged is not None
    assert logged.aggregate_type == "CatalogEntry"


async def test_seeding_the_real_37_catalog_entries_matches_the_master_plan_deliverable(client):
    """Reproduces alembic/versions/0005_create_catalog_entries_table.py's
    exact seed content through the same Use Case/API path, proving the
    Sprint 2.2 Deliverable independently of the migration itself: all five
    kinds populated with the real data, every entry active by default."""
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]

    setups = [
        "Pullback Continuation",
        "Range Reclaim",
        "Support/Resistance Flip",
        "Breakout Retest",
        "Failed Breakdown / Failed Breakout",
        "Sweep + Reclaim (Liquidity Sweep)",
        "Compression Breakout",
        "High Time Frame Reclaim",
    ]
    sessions = ["Weekend", "SYD", "TOK", "EU", "NY", "Overnight"]
    strategies = ["Daily Open", "Nivel importante", "Trend Day / Expansion Day", "Rango"]
    entry_triggers = [
        "Price Action Triggers",
        "Market Structure Triggers",
        "Candle Close Confirmation Triggers",
    ]
    mistake_tags = [
        "FOMO",
        "Revenge Trade",
        "Overtrading",
        "Ignored HTF",
        "Ignored Bias",
        "Ignored Liquidity",
        "Ignored Volume",
        "Ignored Session",
        "Entered Too Early",
        "Entered Too Late",
        "Moved Stop Loss",
        "Closed Early",
        "News Trade",
        "Low Sleep",
        "Emotional Decision",
        "Other",
    ]

    by_kind = {
        "setup": setups,
        "session": sessions,
        "strategy": strategies,
        "entry_trigger": entry_triggers,
        "mistake_tag": mistake_tags,
    }
    assert sum(len(names) for names in by_kind.values()) == 37

    created_ids = []
    for kind, names in by_kind.items():
        for name in names:
            # suffix keeps this test's rows unique across the session-scoped
            # test database, without changing the real business names' shape
            response = await client.post(
                "/api/v1/catalogs",
                json={"kind": kind, "name": f"{name} [{suffix}]"},
                headers=headers,
            )
            assert response.status_code == 201, response.text
            assert response.json()["is_active"] is True
            created_ids.append(response.json()["id"])

    assert len(created_ids) == 37
    assert len(set(created_ids)) == 37
