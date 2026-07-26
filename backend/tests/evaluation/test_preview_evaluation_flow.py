"""
Integration tests: `POST /evaluation/preview` (TRADEOS_API_SPECIFICATION.md
§6.5), run through the real FastAPI app — the first time Evaluation
touches a real database. Exercises the full path: Configuration's
`build_*` factories (Sprint 3.2) reading real criteria/weights/profiles,
`PreviewEvaluationUseCase`'s source_field -> criterion_id translation, and
all five domain engines producing a combined `EvaluationSnapshot`.

Same client/auth fixtures as
tests/configuration/test_configuration_flow.py (unique ids per test,
session-scoped postgres_container).
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
    email = f"eval-{uuid.uuid4()}@example.com"
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
    """Sets up a fresh, published configuration version with exactly one
    criterion (weight=1.0) per engine, all keyed off `suffix` to avoid
    collisions with rows other tests leave behind in the shared,
    session-scoped database."""
    criteria: dict[str, tuple[str, str]] = {}
    for engine in ("confidence", "quality", "execution", "market_context"):
        criteria[engine] = await _create_criterion(client, headers, engine, suffix)
    criteria["bias"] = await _create_criterion(
        client,
        headers,
        "bias",
        suffix,
        category_map={"Bullish": 50, "Bearish": -50},
    )

    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-{suffix}"},
        headers=headers,
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


async def test_preview_evaluation_returns_all_five_engines(client):
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )

    checklist_answers = {
        criteria["confidence"][1]: "Yes",
        criteria["quality"][1]: "No",
        criteria["execution"][1]: "Yes",
        criteria["market_context"][1]: "Yes",
        criteria["bias"][1]: "Bullish",
    }
    response = await client.post(
        "/api/v1/evaluation/preview",
        json={"checklist_answers": checklist_answers, "scoring_profile": PROFILE},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["confidence"]["score"] == 100
    assert body["confidence"]["grade"] == "A+"
    assert body["confidence"]["breakdown"][0]["criterion_id"] == criteria["confidence"][0]
    assert body["quality"]["score"] == 0
    assert body["execution"]["score"] == 100
    assert body["market_context"]["score"] == 100
    assert body["bias"]["score"] == 50
    assert "grade" not in body["bias"]


async def test_preview_evaluation_source_field_translation(client):
    """The request is keyed by source_field; the response breakdown is
    keyed by the stable criterion_id -- proving PreviewEvaluationUseCase's
    translation actually ran, not just that the request was accepted."""
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    _version_id, criteria = await _published_version_with_one_criterion_per_engine(
        client, headers, suffix
    )
    confidence_id, confidence_source_field = criteria["confidence"]

    response = await client.post(
        "/api/v1/evaluation/preview",
        json={
            "checklist_answers": {confidence_source_field: "Yes"},
            "scoring_profile": PROFILE,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    breakdown = response.json()["confidence"]["breakdown"]
    assert len(breakdown) == 1
    assert breakdown[0]["criterion_id"] == confidence_id


async def test_preview_evaluation_source_field_fans_out_to_multiple_criteria(client):
    """One real checklist field can back more than one engine's criterion
    at once (e.g. the real Excel's `dxy` field feeds both Market Context's
    weighted average and Bias's raw-sum GROSS_SCORE) -- a single answer
    must reach every criterion referencing that source_field, not just the
    last one PreviewEvaluationUseCase happens to see while grouping."""
    headers = await _auth_headers(client)
    suffix = uuid.uuid4().hex[:8]
    shared_source_field = f"shared_{suffix}_field"

    market_context_id = f"market_context.shared_{suffix}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": market_context_id,
            "engine_type_code": "market_context",
            "name": "Shared Market Context",
            "source_field": shared_source_field,
            "min_value": 0,
            "max_value": 100,
            "category_map": {"Yes": 100, "No": 0},
        },
        headers=headers,
    )
    bias_id = f"bias.shared_{suffix}"
    await client.post(
        "/api/v1/configuration/scoring-criteria",
        json={
            "id": bias_id,
            "engine_type_code": "bias",
            "name": "Shared Bias",
            "source_field": shared_source_field,
            "min_value": 0,
            "max_value": 100,
            "category_map": {"Yes": 50, "No": -50},
        },
        headers=headers,
    )

    version_response = await client.post(
        "/api/v1/configuration/versions",
        json={"version_label": f"v-shared-{suffix}"},
        headers=headers,
    )
    version_id = version_response.json()["id"]
    for criterion_id in (market_context_id, bias_id):
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

    response = await client.post(
        "/api/v1/evaluation/preview",
        json={"checklist_answers": {shared_source_field: "Yes"}, "scoring_profile": PROFILE},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["market_context"]["score"] == 100
    assert body["market_context"]["breakdown"][0]["criterion_id"] == market_context_id
    assert body["bias"]["score"] == 50
    assert body["bias"]["breakdown"][0]["criterion_id"] == bias_id


async def test_preview_evaluation_unrecognized_scoring_profile_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/evaluation/preview",
        json={"checklist_answers": {}, "scoring_profile": "not_a_real_profile"},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


async def test_preview_evaluation_malformed_checklist_answers_returns_422(client):
    headers = await _auth_headers(client)
    response = await client.post(
        "/api/v1/evaluation/preview",
        json={"checklist_answers": {"x": {"nested": "object"}}, "scoring_profile": PROFILE},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


async def test_preview_evaluation_requires_authentication(client):
    response = await client.post(
        "/api/v1/evaluation/preview",
        json={"checklist_answers": {}, "scoring_profile": PROFILE},
    )
    assert response.status_code == 401
