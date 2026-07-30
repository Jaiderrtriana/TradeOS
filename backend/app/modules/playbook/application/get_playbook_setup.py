"""
GetPlaybookSetupUseCase — `TRADEOS_API_SPECIFICATION.md` §6.8,
`GET /playbook-setups/{id}`: "Full detail, including live performance...
fetched by this endpoint calling the Statistics module's by-dimension
capability internally... never stored on the Playbook Setup itself"
(Domain Model §8.8).

Composition, never duplication: calls Statistics' own `GetStatisticsByDimensionUseCase`
(via `build_get_statistics_by_dimension_use_case`, Statistics' Application
layer -- never Trading's repository directly, `TRADEOS_SYSTEM_ARCHITECTURE.md`
§3.3) with `dimension="setup"`, then selects the one group whose
`dimension_value` equals this Playbook Setup's own `catalog_entry_id` --
the *same identifier* on both sides, which is exactly what the Sprint
7.1 Exit Criteria requires to hold byte-for-byte
(`str(setup.catalog_entry_id) == group.dimension_value`).

`name` is resolved the same way `GetMistakeRankingUseCase` (Sprint 5.2)
already resolves a catalog-backed display name -- transitively, via
`GetCatalogEntryUseCase`, since `PlaybookSetup` owns no `name` column of
its own (`TRADEOS_DATABASE_DESIGN.md` §6.15).

If no group is found (no Trades reference this setup's catalog entry
yet), an all-`None`/`total_pnl=0` `StatisticsSummary` is built locally --
the same shape `aggregate_statistics([])` already produces for a
fresh user, never a different "no data" representation invented here.
"""

import uuid
from dataclasses import dataclass

from app.modules.configuration.application.get_catalog_entry import GetCatalogEntryUseCase
from app.modules.playbook.domain.playbook_setup import PlaybookSetup
from app.modules.playbook.domain.playbook_setup_attachment import PlaybookSetupAttachment
from app.modules.playbook.infrastructure.repository import (
    PlaybookSetupAttachmentRepository,
    PlaybookSetupRepository,
)
from app.modules.statistics.application.get_statistics_by_dimension import (
    GetStatisticsByDimensionUseCase,
)
from app.modules.statistics.domain.statistics_aggregation import StatisticsSummary
from app.platform.errors import NotFoundError

SETUP_DIMENSION = "setup"

_EMPTY_PERFORMANCE = StatisticsSummary(
    win_rate=None,
    expectancy_r=None,
    average_r=None,
    profit_factor_r=None,
    total_pnl=0.0,
    average_confidence_score=None,
    average_quality_score=None,
    average_execution_score=None,
    average_market_context_score=None,
    average_bias_score=None,
)


@dataclass(frozen=True)
class PlaybookSetupDetail:
    setup: PlaybookSetup
    name: str
    attachments: list[PlaybookSetupAttachment]
    performance: StatisticsSummary


class GetPlaybookSetupUseCase:
    def __init__(
        self,
        playbook_setup_repository: PlaybookSetupRepository,
        attachment_repository: PlaybookSetupAttachmentRepository,
        get_catalog_entry_use_case: GetCatalogEntryUseCase,
        get_statistics_by_dimension_use_case: GetStatisticsByDimensionUseCase,
    ) -> None:
        self._playbook_setups = playbook_setup_repository
        self._attachments = attachment_repository
        self._get_catalog_entry = get_catalog_entry_use_case
        self._get_statistics_by_dimension = get_statistics_by_dimension_use_case

    async def execute(self, user_id: uuid.UUID, setup_id: uuid.UUID) -> PlaybookSetupDetail:
        setup = await self._playbook_setups.get_by_id(setup_id)
        if setup is None:
            raise NotFoundError(f"No playbook setup with id '{setup_id}'.")

        catalog_entry = await self._get_catalog_entry.execute(setup.catalog_entry_id)
        # A Playbook Setup's linked catalog entry is enforced to exist by
        # the FK at creation time and is never hard-deleted (DI-10) --
        # `None` here would be a genuine data-integrity gap, never
        # expected in practice, same defensive posture already documented
        # in `GetStatisticsByDimensionUseCase`.
        name = catalog_entry.name if catalog_entry is not None else str(setup.catalog_entry_id)

        attachments = await self._attachments.list_by_setup_id(setup_id)

        groups = await self._get_statistics_by_dimension.execute(user_id, SETUP_DIMENSION)
        matching_group = next(
            (g for g in groups if g.dimension_value == str(setup.catalog_entry_id)), None
        )
        performance = matching_group.summary if matching_group is not None else _EMPTY_PERFORMANCE

        return PlaybookSetupDetail(
            setup=setup, name=name, attachments=attachments, performance=performance
        )
