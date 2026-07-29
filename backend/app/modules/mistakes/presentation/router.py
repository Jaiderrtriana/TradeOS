"""
Mistakes presentation: `GET /mistakes/ranking` — `TRADEOS_API_
SPECIFICATION.md` §6.9. Read-only; no write endpoint exists in this
module (tagging happens through the Trades module, §6.4).

No pagination envelope — a bare JSON array, same precedent as
`GET /configuration/scoring-criteria`/`/scoring-profiles`: a catalog-
bounded list (one row per distinct tagged Mistake Tag), architecturally
analogous to Statistics' on-demand computed reads (ADR-04/KDD-04), not
to a growing row-scale collection like Trades/Journal.

`sort` reorders the *returned list* only — it never changes any entry's
`priority` value, which is always the tag's fixed rank by `total_cost_r`
ascending (Sprint 5.2 approved decision, see `mistakes/domain/
mistake_ranking.py`'s own docstring).
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.configuration.application.list_catalog_entries import (
    build_list_catalog_entries_use_case,
)
from app.modules.mistakes.application.get_mistake_ranking import (
    GetMistakeRankingUseCase,
    MistakeRankingResult,
)
from app.modules.mistakes.presentation.schemas import MistakeRankingEntryResponse
from app.modules.trading.application.list_mistake_occurrences import (
    build_list_mistake_occurrences_use_case,
)
from app.platform.db.session import get_db_session
from app.platform.errors import UnprocessableEntityError
from app.platform.security.dependencies import get_current_user_id

router = APIRouter(prefix="/mistakes", tags=["mistakes"])

_SORT_KEYS = {
    # `total_cost_r is None` (an all-still-open tag) always sorts last,
    # in both directions -- "no data yet" never means "first", matching
    # the same "None sorts last" convention `mistake_ranking.py`'s own
    # `rank_mistakes` already applies for `priority`.
    "cost": lambda r: (
        r.total_cost_r is None,
        r.total_cost_r if r.total_cost_r is not None else 0.0,
    ),
    "-cost": lambda r: (
        r.total_cost_r is None,
        -r.total_cost_r if r.total_cost_r is not None else 0.0,
    ),
    "frequency": lambda r: r.frequency,
    "-frequency": lambda r: -r.frequency,
}


@router.get("/ranking", response_model=list[MistakeRankingEntryResponse])
async def get_mistake_ranking(
    session: AsyncSession = Depends(get_db_session),
    user_id: UUID = Depends(get_current_user_id),
    sort: str = "cost",
) -> list[MistakeRankingEntryResponse]:
    sort_key = _SORT_KEYS.get(sort)
    if sort_key is None:
        # `cost`/`-cost`/`frequency`/`-frequency` are the only fields
        # this endpoint's own response actually has -- no other field is
        # invented as sortable.
        raise UnprocessableEntityError(f"Unsupported sort field: '{sort}'.")

    use_case = GetMistakeRankingUseCase(
        build_list_mistake_occurrences_use_case(session),
        build_list_catalog_entries_use_case(session),
    )
    results = await use_case.execute(user_id)
    ordered = sorted(results, key=sort_key)
    return [_mistake_ranking_response(result) for result in ordered]


def _mistake_ranking_response(result: MistakeRankingResult) -> MistakeRankingEntryResponse:
    return MistakeRankingEntryResponse(
        catalog_entry_id=result.catalog_entry_id,
        name=result.name,
        is_active=result.is_active,
        frequency=result.frequency,
        total_cost_r=result.total_cost_r,
        priority=result.priority,
    )
