"""
StatisticsAggregationService — `TRADEOS_DOMAIN_MODEL.md` §12.2: "Computes
Win Rate, Expectancy, Profit Factor, Average R, and related metrics over
any set of Trades. Written once, generically, and reused for every
grouping." Pure domain functions, not a class — stateless, constructed
fresh per call, same shape as `mistake_ranking.rank_mistakes` (Sprint
5.2) and `evaluation_engine.evaluate()`. No repository access, no SQL,
no FastAPI — every input arrives already resolved as a plain
`StatisticsFact`.

Approved resolutions (Sprint 6.1 — no document defines precise formulas
for these; confirmed absent across the Domain Model, Backend Blueprint,
API Specification, and Product Bible before implementation began):

- **Win Rate** = count(result == "tp") / count(closed trades), where
  "closed" means `result != "open"` (Domain Model §2.3: "the proportion
  of closed Trades that resulted in TP" — a break-even trade is a closed
  Trade, so it is in the denominator, but never in the numerator; it is
  not separately "counted as a loss," it simply isn't a win). Returned as
  a raw 0-1 ratio, never pre-multiplied by 100 — same convention as
  `Trade.captured_pct`.
- **Expectancy** = **Average R** = the arithmetic mean of `r_multiple`
  across every closed Trade (open Trades excluded — `r_multiple` is
  `None` for them, per `compute_r_multiple`; break-even Trades
  participate with their own real `r_multiple`, typically near zero).
  These two Domain-Model-named metrics are numerically identical under
  this resolution — both fields still exist, because the Domain Model
  names them as two separate outputs, even though this formula makes
  them equal.
- **Profit Factor** = `gross_profit_r / gross_loss_r`, where
  `gross_profit_r` is the sum of every positive `r_multiple` and
  `gross_loss_r` is the sum of the *absolute value* of every negative
  `r_multiple` (R-multiple-based, not `realized_pnl`-based — consistent
  with Expectancy/Average R, same reasoning Sprint 5.2 approved for
  Mistakes' "cost"). `gross_loss_r == 0` (no losing trades) returns
  `None` — never `Infinity`, `NaN`, or an exception, same convention
  `compute_r_multiple` already established for its own division.
- **Total P&L** = sum of `realized_pnl` across every non-deleted Trade
  (open Trades included — `realized_pnl` defaults to `0` for them, so
  this is a no-op inclusion, not a special case).
- **Average Engine scores** = arithmetic mean per engine, across every
  non-deleted Trade's *current* Evaluation Snapshot, skipping `None`
  scores — same "`None` means not yet computable, skip it" convention
  used everywhere else in this codebase (`captured_pct`,
  `potential_left_r`, Mistakes' cost).
- **Null-dimension bucketing** (`aggregate_by_dimension`): Trades with no
  `strategy_id`/`setup_id`/`session_id` are grouped into an explicit
  `"unassigned"` bucket, never silently dropped. `direction` is never
  `NULL` on a Trade, so it never produces this bucket.
"""

import uuid
from dataclasses import dataclass

UNASSIGNED = "unassigned"
DIMENSIONS = ("strategy", "setup", "session", "direction")


@dataclass(frozen=True)
class StatisticsFact:
    """One Trade's contribution to an aggregation — deliberately not
    Trading's own `TradeStatisticsRecord`; this domain layer depends on
    nothing outside itself. `result` uses the same literal strings
    Trading's own schema does (`"open"`/`"tp"`/`"sl"`/`"be"`) as a
    structural literal, never importing `trading.domain.trade`'s
    constants — same precedent `TagMistakeUseCase` already established
    (Sprint 4.3) for `"mistake_tag"`."""

    result: str
    realized_pnl: float
    r_multiple: float | None
    strategy_id: uuid.UUID | None
    setup_id: uuid.UUID | None
    session_id: uuid.UUID | None
    direction: str
    confidence_score: float | None
    quality_score: float | None
    execution_score: float | None
    market_context_score: float | None
    bias_score: float | None


@dataclass(frozen=True)
class StatisticsSummary:
    win_rate: float | None
    expectancy_r: float | None
    average_r: float | None
    profit_factor_r: float | None
    total_pnl: float
    average_confidence_score: float | None
    average_quality_score: float | None
    average_execution_score: float | None
    average_market_context_score: float | None
    average_bias_score: float | None


@dataclass(frozen=True)
class DimensionStatistics:
    """`dimension_value` is the raw grouping key: a `CatalogEntry` id (as
    a string) for strategy/setup/session, `"unassigned"` for a null one,
    or the literal direction (`"long"`/`"short"`). Resolving a catalog id
    into a display name is the Application layer's job (via
    Configuration's `build_list_catalog_entries_use_case`), not this
    domain function's — it never sees a catalog entry at all."""

    dimension_value: str
    summary: StatisticsSummary


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def aggregate_statistics(facts: list[StatisticsFact]) -> StatisticsSummary:
    closed_facts = [f for f in facts if f.result != "open"]

    win_rate = (
        sum(1 for f in closed_facts if f.result == "tp") / len(closed_facts)
        if closed_facts
        else None
    )

    r_multiples = [f.r_multiple for f in closed_facts if f.r_multiple is not None]
    expectancy_r = _mean(r_multiples)
    average_r = (
        expectancy_r  # Numerically identical under the approved formula -- see module docstring.
    )

    gross_profit_r = sum(r for r in r_multiples if r > 0)
    gross_loss_r = sum(-r for r in r_multiples if r < 0)
    profit_factor_r = gross_profit_r / gross_loss_r if gross_loss_r > 0 else None

    total_pnl = sum(f.realized_pnl for f in facts)

    return StatisticsSummary(
        win_rate=win_rate,
        expectancy_r=expectancy_r,
        average_r=average_r,
        profit_factor_r=profit_factor_r,
        total_pnl=total_pnl,
        average_confidence_score=_mean(
            [f.confidence_score for f in facts if f.confidence_score is not None]
        ),
        average_quality_score=_mean(
            [f.quality_score for f in facts if f.quality_score is not None]
        ),
        average_execution_score=_mean(
            [f.execution_score for f in facts if f.execution_score is not None]
        ),
        average_market_context_score=_mean(
            [f.market_context_score for f in facts if f.market_context_score is not None]
        ),
        average_bias_score=_mean([f.bias_score for f in facts if f.bias_score is not None]),
    )


def _dimension_key(fact: StatisticsFact, dimension: str) -> str:
    if dimension == "strategy":
        return str(fact.strategy_id) if fact.strategy_id is not None else UNASSIGNED
    if dimension == "setup":
        return str(fact.setup_id) if fact.setup_id is not None else UNASSIGNED
    if dimension == "session":
        return str(fact.session_id) if fact.session_id is not None else UNASSIGNED
    if dimension == "direction":
        return fact.direction
    # Unreachable in practice -- the presentation layer validates
    # `dimension` against `DIMENSIONS` before this function is ever
    # called (same "validate at the router, never pass an invalid value
    # down" discipline as Trades'/Mistakes' own `sort` param). A plain
    # `ValueError`, not `UnprocessableEntityError`, keeps this domain
    # module free of any `app.platform` import.
    raise ValueError(f"Unsupported dimension: '{dimension}'")


def aggregate_by_dimension(
    facts: list[StatisticsFact], dimension: str
) -> list[DimensionStatistics]:
    groups: dict[str, list[StatisticsFact]] = {}
    for fact in facts:
        key = _dimension_key(fact, dimension)
        groups.setdefault(key, []).append(fact)

    return [
        DimensionStatistics(dimension_value=key, summary=aggregate_statistics(group_facts))
        for key, group_facts in groups.items()
    ]
