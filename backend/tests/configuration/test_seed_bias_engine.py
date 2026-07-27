"""
Integration tests for `scripts/seed_configuration.py`'s Bias Engine data
(Sprint 3.2, real data proposal — see CHANGELOG.md). First automated
coverage of this seed script at all (previously "run manually, verify by
eye"): idempotency, per-profile weight sums, and that the fan-out fix
(`PreviewEvaluationUseCase`) actually works against the real seeded data,
not just synthetic fixtures.

`seed()` opens its own session via the module-level `SessionLocal`
(designed to be run standalone, `PYTHONPATH=. poetry run python
scripts/seed_configuration.py ...`, against the real configured database)
rather than accepting an injected session -- these tests monkeypatch
`scripts.seed_configuration.SessionLocal` to point at a database they
provision themselves, letting `seed()` run unmodified against a test
database.

Deliberately does **not** reuse `tests/conftest.py`'s shared,
session-scoped `postgres_container`/`db_session`: `seed()`'s own
idempotency guard ("skip if any published configuration version already
exists") is a whole-database invariant, and many other tests in this
suite (`test_configuration_flow.py`'s publish tests,
`test_preview_evaluation_flow.py`'s fixtures) already publish their own
versions there. Sharing that database would make `seed()` silently skip
real seeding whenever this file happens to run after one of those --
exactly the kind of test-order-dependent flakiness a dedicated,
function-scoped container avoids.
"""

import sys
import uuid
from collections import defaultdict
from pathlib import Path

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.modules.configuration.application.get_configuration_version import (
    build_get_configuration_version_use_case,
)
from app.modules.configuration.application.list_configuration_weights import (
    build_list_configuration_weights_use_case,
)
from app.modules.configuration.application.list_scoring_criteria import (
    build_list_scoring_criteria_use_case,
)
from app.modules.configuration.application.list_scoring_profiles import (
    build_list_scoring_profiles_use_case,
)
from app.modules.configuration.infrastructure import models as configuration_models
from app.modules.evaluation.application.preview_evaluation import PreviewEvaluationUseCase
from app.modules.identity.domain.user_account import UserAccount
from app.modules.identity.infrastructure.repository import UserAccountRepository
from app.platform.db.base import Base

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import scripts.seed_configuration as seed_configuration  # noqa: E402
from scripts.seed_configuration import BIAS_CRITERIA, BIAS_WEIGHT  # noqa: E402

PROFILES = ("day_trading", "swing_trading", "scalping")


@pytest_asyncio.fixture
async def bias_seed_session(monkeypatch):
    """A dedicated, empty Postgres instance -- never shared with the rest
    of the suite -- so `seed()`'s own "already published" idempotency
    guard reflects only what this test itself seeds."""
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        engine = create_async_engine(container.get_connection_url())
        async with engine.begin() as conn:
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS platform"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS identity"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS preferences"))
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS configuration"))
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            session.add_all(
                [
                    configuration_models.EngineTypeModel(
                        code="confidence", display_name="Trade Confidence", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="quality", display_name="Trade Quality", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="execution", display_name="Execution Score", is_signed=False
                    ),
                    configuration_models.EngineTypeModel(
                        code="market_context",
                        display_name="Market Context Score",
                        is_signed=False,
                    ),
                    configuration_models.EngineTypeModel(
                        code="bias", display_name="Bias Index", is_signed=True
                    ),
                    configuration_models.ScoringProfileModel(
                        code="day_trading", display_name="Day Trading"
                    ),
                    configuration_models.ScoringProfileModel(
                        code="swing_trading", display_name="Swing Trading"
                    ),
                    configuration_models.ScoringProfileModel(
                        code="scalping", display_name="Scalping"
                    ),
                ]
            )
            await session.commit()

            monkeypatch.setattr(
                seed_configuration,
                "SessionLocal",
                async_sessionmaker(bind=engine, expire_on_commit=False),
            )
            yield session
        await engine.dispose()


async def _create_user(session) -> uuid.UUID:
    user = UserAccount(email=f"seed-{uuid.uuid4()}@example.com", password_hash="x")
    await UserAccountRepository(session).add(user)
    await session.commit()
    return user.id


async def test_seed_bias_is_idempotent_and_weights_sum_correctly(bias_seed_session):
    user_id = await _create_user(bias_seed_session)
    version_label = f"v-bias-{uuid.uuid4().hex[:8]}"

    await seed_configuration.seed(user_id, version_label)
    # Second call: a published version already exists, so `seed()` must
    # exit early without erroring or creating a duplicate version/rows.
    await seed_configuration.seed(user_id, f"v-bias-second-{uuid.uuid4().hex[:8]}")

    result = await bias_seed_session.execute(
        select(configuration_models.ScoringCriterionModel).where(
            configuration_models.ScoringCriterionModel.engine_type_code == "bias"
        )
    )
    bias_criteria = result.scalars().all()
    assert len(bias_criteria) == len(BIAS_CRITERIA) == 46

    versions_result = await bias_seed_session.execute(
        select(configuration_models.ScoringConfigurationVersionModel).where(
            configuration_models.ScoringConfigurationVersionModel.status == "published"
        )
    )
    assert len(versions_result.scalars().all()) == 1, "seed() must not publish a second version"

    weights_result = await bias_seed_session.execute(
        select(configuration_models.ScoringWeightModel).where(
            configuration_models.ScoringWeightModel.criterion_id.in_([c[0] for c in BIAS_CRITERIA])
        )
    )
    sums: dict[str, float] = defaultdict(float)
    for weight_row in weights_result.scalars().all():
        sums[weight_row.profile_code] += float(weight_row.weight)
    assert set(sums) == set(PROFILES)
    for profile_code in PROFILES:
        assert (
            abs(sums[profile_code] - 1.0) < 1e-9
        ), f"Bias weights for {profile_code} sum to {sums[profile_code]}, expected 1.0"
        # Exactly 35 active criteria per profile (46 rows, 11 duplicated
        # for the Swing-vs-No-Swing split -- only one variant is active
        # per profile).
        assert abs(sums[profile_code] / BIAS_WEIGHT - 35) < 1e-6


async def test_preview_evaluation_fans_out_real_seeded_dxy_to_market_context_and_bias(
    bias_seed_session,
):
    """The real seed shares `dxy` between `market_context.dxy` and
    `bias.dxy` -- proves the Sprint 3.2 fan-out fix works against real
    data, not just the synthetic fixture already covered in
    test_preview_evaluation_flow.py."""
    user_id = await _create_user(bias_seed_session)
    await seed_configuration.seed(user_id, f"v-bias-{uuid.uuid4().hex[:8]}")

    use_case = PreviewEvaluationUseCase(
        build_get_configuration_version_use_case(bias_seed_session),
        build_list_scoring_criteria_use_case(bias_seed_session),
        build_list_configuration_weights_use_case(bias_seed_session),
        build_list_scoring_profiles_use_case(bias_seed_session),
    )
    result = await use_case.execute(
        checklist_answers={"dxy": "Strong Bullish"},
        scoring_profile="day_trading",
    )

    market_context_row = next(
        row for row in result.market_context.breakdown if row.criterion_id == "market_context.dxy"
    )
    assert market_context_row.raw_value == "Strong Bullish"

    bias_row = next(row for row in result.bias.breakdown if row.criterion_id == "bias.dxy")
    assert bias_row.raw_value == "Strong Bullish"
    # Real day_trading category point for DXY "Strong Bullish" is -3
    # (BIAS_CRITERIA); with only this one criterion answered, weight=1/35
    # is the only active/answered weight, so the weighted average equals
    # -3 exactly, before BIAS_SCALE_FACTOR=20.
    assert bias_row.contribution == -3 * BIAS_WEIGHT
