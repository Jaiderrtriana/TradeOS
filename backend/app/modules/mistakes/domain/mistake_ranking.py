"""
MistakePriorityRankingService — `TRADEOS_DOMAIN_MODEL.md` §12.3: "Given
the set of Trades referencing each MistakeTag, computes frequency, total
cost, and a combined priority ranking." A pure domain function, not a
class — stateless, constructed fresh per call (`TRADEOS_BACKEND_
BLUEPRINT.md` Section 5: "Lifecycle: all four [domain services] are
constructed fresh per invocation... none holds state across calls"),
same shape as `evaluation_engine.evaluate()`.

Approved resolution (Sprint 5.2 — no document defines a precise formula
for "cost" or "priority"; both were confirmed absent across the Domain
Model, Backend Blueprint, API Specification, and Product Bible before
implementation began):
- **Cost** = sum of `r_multiple` (risk-normalized, not `realized_pnl`)
  across every Trade tagged with a given Mistake Tag — including Trades
  where the tagged mistake didn't end up costing the trade (a net-signed
  total, not a magnitude-of-losses-only figure).
- **Frequency** = count of `trade_mistakes` rows, regardless of whether
  the tagged Trade is still open (an open Trade's `r_multiple` is `None`
  — it counts toward frequency but contributes nothing to `total_cost_r`,
  the same "None means not yet computable" treatment already established
  for `captured_pct`/`potential_left_r`).
- **Priority** = explicitly **not** a combined formula — none is
  justified by any document, and none is invented here. It is the tag's
  fixed, stable rank position when every tag is ordered by `total_cost_r`
  ascending (most costly/most negative first) — the system's own default
  ordering (`TRADEOS_FRONTEND_BLUEPRINT.md` §11: "Sorting: By priority
  (default)"; §12: "which mistake actually costs me the most"). This
  value is computed once here and never recalculated when the caller
  later re-sorts the *displayed* list by Frequency or Cost — Priority
  keeps meaning "rank by the system's primary metric," not "current
  table row index" (approved decision, Sprint 5.2).
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MistakeOccurrence:
    """One `trade_mistakes` row's contribution: which tag, and the
    tagged Trade's `r_multiple` (`None` if the Trade is still open)."""

    catalog_entry_id: uuid.UUID
    r_multiple: float | None


@dataclass(frozen=True)
class MistakeRankingEntry:
    catalog_entry_id: uuid.UUID
    frequency: int
    total_cost_r: float | None
    priority: int


def rank_mistakes(occurrences: list[MistakeOccurrence]) -> list[MistakeRankingEntry]:
    """Groups occurrences by tag, aggregates frequency/cost, and assigns
    each tag its stable `priority` position (cost-ascending). Returns
    entries already in that same priority order — the natural "priority"
    view — leaving any *display* re-sort (by Frequency instead) to the
    caller, which must reorder the returned list without altering any
    entry's `priority` value."""
    grouped: dict[uuid.UUID, list[MistakeOccurrence]] = {}
    for occurrence in occurrences:
        grouped.setdefault(occurrence.catalog_entry_id, []).append(occurrence)

    aggregated: list[tuple[uuid.UUID, int, float | None]] = []
    for catalog_entry_id, tag_occurrences in grouped.items():
        frequency = len(tag_occurrences)
        computable_costs = [o.r_multiple for o in tag_occurrences if o.r_multiple is not None]
        total_cost_r = sum(computable_costs) if computable_costs else None
        aggregated.append((catalog_entry_id, frequency, total_cost_r))

    def priority_sort_key(item: tuple[uuid.UUID, int, float | None]) -> tuple[int, float, str]:
        catalog_entry_id, _frequency, total_cost_r = item
        # Tags with no computable cost (every occurrence still open) sort
        # last -- there is nothing yet to prioritize fixing. Ties (equal
        # cost, or both None) break on catalog_entry_id for a
        # deterministic, reproducible order.
        if total_cost_r is None:
            return (1, 0.0, str(catalog_entry_id))
        return (0, total_cost_r, str(catalog_entry_id))

    ordered = sorted(aggregated, key=priority_sort_key)

    return [
        MistakeRankingEntry(
            catalog_entry_id=catalog_entry_id,
            frequency=frequency,
            total_cost_r=total_cost_r,
            priority=index + 1,
        )
        for index, (catalog_entry_id, frequency, total_cost_r) in enumerate(ordered)
    ]
