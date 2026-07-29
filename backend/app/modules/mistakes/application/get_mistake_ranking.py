"""
GetMistakeRankingUseCase — `TRADEOS_BACKEND_BLUEPRINT.md` §4.8's compact
row ("GetMistakeRanking | Mistakes | none (pure read) | none");
`TRADEOS_API_SPECIFICATION.md` §6.9, `GET /mistakes/ranking`.

Combines two cross-module, read-only dependencies (`TRADEOS_BACKEND_
BLUEPRINT.md` §3.8: "Dependencies: Trading (read-only), Configuration
(read-only, for tag names/metadata)"), both reached exclusively through
their owning module's own Application-layer factory, never a repository
directly (`TRADEOS_SYSTEM_ARCHITECTURE.md` §3.3):
`ListMistakeOccurrencesUseCase` (Trading) for each tagged Trade's cost,
`ListCatalogEntriesUseCase` (Configuration, `kind=mistake_tag`) for each
tag's `name`/`is_active` — including inactive tags, so a deactivated
mistake's historical occurrences still appear, ranked (`TRADEOS_
IMPLEMENTATION_MASTER_PLAN.md` §10's regression-test note: "excludes
deactivated tags' *new* use while still counting their historical
occurrences" — already enforced by `TagMistakeUseCase`, Sprint 4.3;
this Use Case's own job is simply to never filter a deactivated tag out
of the ranking).

Only tags with at least one occurrence appear (`rank_mistakes` only
produces entries for tags actually present in `trade_mistakes`) — a
zero-frequency mistake tag was never tagged, so it has nothing to rank.
"""

import uuid
from dataclasses import dataclass

from app.modules.mistakes.domain.mistake_ranking import (
    MistakeOccurrence,
    MistakeRankingEntry,
    rank_mistakes,
)
from app.modules.configuration.application.list_catalog_entries import ListCatalogEntriesUseCase
from app.modules.trading.application.list_mistake_occurrences import ListMistakeOccurrencesUseCase

MISTAKE_TAG_KIND = "mistake_tag"


@dataclass(frozen=True)
class MistakeRankingResult:
    catalog_entry_id: uuid.UUID
    name: str
    is_active: bool
    frequency: int
    total_cost_r: float | None
    priority: int


class GetMistakeRankingUseCase:
    def __init__(
        self,
        list_mistake_occurrences_use_case: ListMistakeOccurrencesUseCase,
        list_catalog_entries_use_case: ListCatalogEntriesUseCase,
    ) -> None:
        self._list_mistake_occurrences = list_mistake_occurrences_use_case
        self._list_catalog_entries = list_catalog_entries_use_case

    async def execute(self, user_id: uuid.UUID) -> list[MistakeRankingResult]:
        occurrences = await self._list_mistake_occurrences.execute(user_id)
        mistake_tags = await self._list_catalog_entries.execute(MISTAKE_TAG_KIND)
        tags_by_id = {tag.id: tag for tag in mistake_tags}

        ranked: list[MistakeRankingEntry] = rank_mistakes(
            [
                MistakeOccurrence(catalog_entry_id=o.catalog_entry_id, r_multiple=o.r_multiple)
                for o in occurrences
            ]
        )

        results: list[MistakeRankingResult] = []
        for entry in ranked:
            tag = tags_by_id.get(entry.catalog_entry_id)
            # A `trade_mistakes` row always references a real, existing
            # catalog entry (DI-10: deactivation, never deletion) -- a
            # missing lookup here would be a genuine data-integrity bug,
            # not a request-shape concern, so it fails loudly.
            if tag is None:
                raise RuntimeError(
                    f"trade_mistakes references catalog entry '{entry.catalog_entry_id}', "
                    "which no longer exists."
                )
            results.append(
                MistakeRankingResult(
                    catalog_entry_id=entry.catalog_entry_id,
                    name=tag.name,
                    is_active=tag.is_active,
                    frequency=entry.frequency,
                    total_cost_r=entry.total_cost_r,
                    priority=entry.priority,
                )
            )
        return results
