"""
GetStatisticsByDimensionUseCase — `TRADEOS_API_SPECIFICATION.md` §6.10,
`GET /statistics/by-dimension?dimension=strategy|setup|session|direction`:
"Same metrics, grouped by dimension."

Pure orchestration -- no formula lives here (that's `aggregate_by_
dimension`'s job). For `strategy`/`setup`/`session`, resolves each
group's catalog entry name via Configuration's own `build_list_catalog_
entries_use_case` factory (never Configuration's repository directly),
same pattern `GetMistakeRankingUseCase` already established (Sprint
5.2) for the identical "group by a catalog-entry FK, show its name"
shape. `direction` needs no catalog lookup -- its own value ("long"/
"short") is already the display value, same raw-string convention every
other Trade-facing endpoint already uses.

`build_get_statistics_by_dimension_use_case` (Sprint 7.1) is this
module's first `build_*` factory -- Playbook's `GetPlaybookSetupUseCase`
is the first consumer outside `statistics/presentation/router.py`. No
change to this Use Case's own behavior or to `GET /statistics/by-dimension`'s
HTTP contract.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.list_catalog_entries import (
    ListCatalogEntriesUseCase,
    build_list_catalog_entries_use_case,
)
from app.modules.statistics.application.mapping import to_statistics_fact
from app.modules.statistics.domain.statistics_aggregation import (
    UNASSIGNED,
    StatisticsSummary,
    aggregate_by_dimension,
)
from app.modules.trading.application.list_trade_statistics_facts import (
    ListTradeStatisticsFactsUseCase,
    build_list_trade_statistics_facts_use_case,
)

_CATALOG_BACKED_DIMENSIONS = ("strategy", "setup", "session")


@dataclass(frozen=True)
class DimensionStatisticsResult:
    dimension_value: str
    label: str
    summary: StatisticsSummary


class GetStatisticsByDimensionUseCase:
    def __init__(
        self,
        list_trade_statistics_facts_use_case: ListTradeStatisticsFactsUseCase,
        list_catalog_entries_use_case: ListCatalogEntriesUseCase,
    ) -> None:
        self._list_trade_statistics_facts = list_trade_statistics_facts_use_case
        self._list_catalog_entries = list_catalog_entries_use_case

    async def execute(self, user_id: uuid.UUID, dimension: str) -> list[DimensionStatisticsResult]:
        records = await self._list_trade_statistics_facts.execute(user_id)
        facts = [to_statistics_fact(record) for record in records]
        groups = aggregate_by_dimension(facts, dimension)

        name_by_catalog_entry_id: dict[str, str] = {}
        if dimension in _CATALOG_BACKED_DIMENSIONS:
            entries = await self._list_catalog_entries.execute(dimension)
            name_by_catalog_entry_id = {str(entry.id): entry.name for entry in entries}

        results: list[DimensionStatisticsResult] = []
        for group in groups:
            if group.dimension_value == UNASSIGNED:
                label = "Unassigned"
            elif dimension in _CATALOG_BACKED_DIMENSIONS:
                # A `trade_mistakes`-style reference always names a real,
                # existing catalog entry (DI-10: deactivation, never
                # deletion) -- falling back to the raw id is only a
                # defensive guard against a genuine data-integrity gap,
                # never expected in practice.
                label = name_by_catalog_entry_id.get(group.dimension_value, group.dimension_value)
            else:
                label = group.dimension_value
            results.append(
                DimensionStatisticsResult(
                    dimension_value=group.dimension_value, label=label, summary=group.summary
                )
            )
        return results


def build_get_statistics_by_dimension_use_case(
    session: AsyncSession,
) -> GetStatisticsByDimensionUseCase:
    """Factory exposed so another module's Application layer (Playbook's
    `GetPlaybookSetupUseCase`, Sprint 7.1 -- the first cross-module
    consumer of Statistics) can resolve by-dimension figures without ever
    importing Statistics' or Trading's infrastructure layer directly --
    same pattern as `build_list_trade_statistics_facts_use_case`."""
    return GetStatisticsByDimensionUseCase(
        build_list_trade_statistics_facts_use_case(session),
        build_list_catalog_entries_use_case(session),
    )
