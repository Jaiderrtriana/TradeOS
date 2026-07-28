"""
Regression test for `ReevaluateTradeUseCase`'s concurrency-safety design
(Sprint 4.2, approved): two genuinely concurrent `reevaluate` calls for
the *same* Trade must serialize via `SELECT ... FOR UPDATE` on the Trade
row, never both read the same "current snapshot" and race to supersede
it -- the end state must have exactly one current `EvaluationSnapshot`,
never zero (a lost supersede) and never two (the exact self-conflict
class of bug already found and fixed in
`PublishScoringConfigurationVersionUseCase`, see CHANGELOG.md).

A dedicated, isolated Postgres container and direct Use Case
construction (no HTTP layer) -- matching
tests/configuration/test_publish_concurrency.py's own reasoning:
`asyncio.gather` needs two genuinely independent sessions/connections to
provoke a real database-level race, which a single shared, dependency-
overridden test client cannot provide.
"""

import asyncio
import uuid

import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

from app.modules.configuration.application.create_draft_configuration_version import (
    CreateDraftConfigurationVersionUseCase,
)
from app.modules.configuration.application.create_scoring_criterion import (
    CreateScoringCriterionUseCase,
)
from app.modules.configuration.application.get_catalog_entry import (
    build_get_catalog_entry_use_case,
)
from app.modules.configuration.application.get_configuration_version import (
    build_get_configuration_version_use_case,
)
from app.modules.configuration.application.publish_scoring_configuration_version import (
    PublishScoringConfigurationVersionUseCase,
)
from app.modules.configuration.application.update_draft_weights import UpdateDraftWeightsUseCase
from app.modules.configuration.infrastructure import models as configuration_models
from app.modules.configuration.infrastructure.repository import (
    EngineTypeRepository,
    ScoringConfigurationVersionRepository,
    ScoringCriterionRepository,
    ScoringProfileRepository,
    ScoringWeightRepository,
)
from app.modules.evaluation.application.preview_evaluation import (
    build_preview_evaluation_use_case,
)
from app.modules.trading.application.reevaluate_trade import ReevaluateTradeUseCase
from app.modules.trading.application.register_trade import RegisterTradeUseCase
from app.modules.trading.infrastructure import models as trading_models
from app.modules.trading.infrastructure.repository import (
    ChecklistSnapshotRepository,
    EvaluationSnapshotRepository,
    TradeRepository,
)
from app.platform.db.base import Base
from app.platform.errors import ConflictError, NotFoundError, UnprocessableEntityError
from app.platform.events.dispatcher import dispatcher

PROFILE = "day_trading"
USER_ID = uuid.uuid4()


@pytest_asyncio.fixture
async def concurrency_engine():
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        engine = create_async_engine(container.get_connection_url())
        async with engine.begin() as conn:
            for schema in ("platform", "identity", "preferences", "configuration", "trading"):
                await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
            await conn.run_sync(Base.metadata.create_all)
            # Neither partial unique index is applied by `create_all`
            # (hand-written, not part of any model's own metadata) --
            # created directly here so this test exercises the exact same
            # constraints the real migrations add.
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX ix_scoring_configuration_versions_one_published
                    ON configuration.scoring_configuration_versions ((true))
                    WHERE status = 'published'
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    CREATE UNIQUE INDEX ix_evaluation_snapshots_one_current_per_trade
                    ON trading.evaluation_snapshots (trade_id)
                    WHERE is_current = true
                    """
                )
            )
            # This suite never inserts a real identity.user_accounts row
            # (USER_ID is a bare uuid4) -- both FKs referencing it are
            # dropped so this test can focus purely on the reevaluate
            # race itself, exactly as test_publish_concurrency.py only
            # ever seeds the minimal rows its own race needs.
            await conn.execute(
                text("ALTER TABLE trading.trades DROP CONSTRAINT trades_user_id_fkey")
            )
            await conn.execute(
                text("ALTER TABLE trading.trades DROP CONSTRAINT trades_created_by_user_id_fkey")
            )

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
                        code=PROFILE, display_name="Day Trading"
                    ),
                ]
            )
            await session.commit()

        yield engine
        await engine.dispose()


def _make_session(engine) -> async_sessionmaker:
    return async_sessionmaker(bind=engine, expire_on_commit=False)


async def _create_criterion(session_factory, criterion_id: str, engine_type_code: str) -> str:
    source_field = f"{criterion_id}_field"
    async with session_factory() as session:
        use_case = CreateScoringCriterionUseCase(
            ScoringCriterionRepository(session), EngineTypeRepository(session)
        )
        await use_case.execute(
            id=criterion_id,
            engine_type_code=engine_type_code,
            name=criterion_id,
            source_field=source_field,
            min_value=0,
            max_value=100,
            category_map={"Yes": 100, "No": 0},
        )
        await session.commit()
    return source_field


async def _publish_version_with_weight(session_factory, criterion_id: str, label: str) -> uuid.UUID:
    async with session_factory() as session:
        draft = await CreateDraftConfigurationVersionUseCase(
            ScoringConfigurationVersionRepository(session), ScoringWeightRepository(session)
        ).execute(label)
        await session.commit()
        draft_id = draft.id

    async with session_factory() as session:
        await UpdateDraftWeightsUseCase(
            ScoringConfigurationVersionRepository(session),
            ScoringWeightRepository(session),
            ScoringCriterionRepository(session),
            ScoringProfileRepository(session),
        ).execute(draft_id, criterion_id, PROFILE, 1.0)
        await session.commit()

    async with session_factory() as session:
        await PublishScoringConfigurationVersionUseCase(
            ScoringConfigurationVersionRepository(session),
            ScoringWeightRepository(session),
            ScoringCriterionRepository(session),
            dispatcher,
            session,
        ).execute(draft_id)
        await session.commit()

    return draft_id


async def _register_trade(session_factory, source_field: str) -> uuid.UUID:
    async with session_factory() as session:
        use_case = RegisterTradeUseCase(
            TradeRepository(session),
            ChecklistSnapshotRepository(session),
            EvaluationSnapshotRepository(session),
            build_get_catalog_entry_use_case(session),
            build_get_configuration_version_use_case(session),
            build_preview_evaluation_use_case(session),
            dispatcher,
            session,
        )
        result = await use_case.execute(
            user_id=USER_ID,
            market="EURUSD",
            direction="long",
            entry_price=100.0,
            stop_loss=95.0,
            scoring_profile=PROFILE,
            checklist_answers={source_field: "Yes"},
        )
        await session.commit()
        return result.trade.id


async def _reevaluate(session_factory, trade_id: uuid.UUID):
    async with session_factory() as session:
        use_case = ReevaluateTradeUseCase(
            TradeRepository(session),
            ChecklistSnapshotRepository(session),
            EvaluationSnapshotRepository(session),
            build_get_configuration_version_use_case(session),
            build_preview_evaluation_use_case(session),
            dispatcher,
            session,
        )
        result = await use_case.execute(trade_id, USER_ID, scoring_profile=PROFILE)
        await session.commit()
        return result


async def test_concurrent_reevaluate_calls_never_leave_two_or_zero_current_snapshots(
    concurrency_engine,
):
    session_factory = _make_session(concurrency_engine)
    source_field = await _create_criterion(
        session_factory, "confidence.reevaluate_concurrency", "confidence"
    )
    await _publish_version_with_weight(
        session_factory, "confidence.reevaluate_concurrency", "v-reevaluate-concurrency"
    )
    trade_id = await _register_trade(session_factory, source_field)

    results = await asyncio.gather(
        _reevaluate(session_factory, trade_id),
        _reevaluate(session_factory, trade_id),
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, Exception):
            assert isinstance(
                result, (ConflictError, NotFoundError, UnprocessableEntityError)
            ), f"Unexpected exception from a concurrent reevaluate: {result!r}"

    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(trading_models.EvaluationSnapshotModel).where(
                        trading_models.EvaluationSnapshotModel.trade_id == trade_id
                    )
                )
            )
            .scalars()
            .all()
        )

    # The real regression: exactly 3 rows total (the original registration
    # snapshot + two reevaluate snapshots, serialized one after the other
    # by the row lock), and exactly one of them ever `is_current`.
    assert len(rows) == 3
    current_rows = [row for row in rows if row.is_current]
    assert len(current_rows) == 1
