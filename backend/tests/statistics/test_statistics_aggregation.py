"""
Unit tests: `app/modules/statistics/domain/statistics_aggregation.py` --
pure functions, no DB, no HTTP, same precedent as
`tests/evaluation/test_confidence_engine.py`. Covers the edge cases the
real system never actually produces today (a genuinely `None` engine
score) alongside the formulas already exercised end-to-end in
`test_statistics_flow.py`. Rolling Statistics (Sprint 6.2) is exercised
here at the small window sizes (e.g. 2) the real HTTP endpoint can never
accept (`ROLLING_WINDOWS` restricts it to 10/20/30/50/100/200) --
`select_rolling_window`/`aggregate_rolling` themselves place no such
restriction, since window validation is the presentation layer's job.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.modules.statistics.domain.statistics_aggregation import (
    UNASSIGNED,
    StatisticsFact,
    aggregate_by_dimension,
    aggregate_rolling,
    aggregate_statistics,
    select_rolling_window,
)

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _fact(**overrides) -> StatisticsFact:
    defaults = dict(
        result="tp",
        realized_pnl=0.0,
        r_multiple=1.0,
        strategy_id=None,
        setup_id=None,
        session_id=None,
        direction="long",
        entered_at=_BASE_TIME,
        confidence_score=None,
        quality_score=None,
        execution_score=None,
        market_context_score=None,
        bias_score=None,
    )
    defaults.update(overrides)
    return StatisticsFact(**defaults)


def test_empty_input_returns_all_none():
    summary = aggregate_statistics([])
    assert summary.win_rate is None
    assert summary.expectancy_r is None
    assert summary.average_r is None
    assert summary.profit_factor_r is None
    assert summary.total_pnl == 0
    assert summary.average_confidence_score is None


def test_win_rate_counts_break_even_as_closed_but_not_a_win():
    facts = [
        _fact(result="tp", r_multiple=2.0),
        _fact(result="sl", r_multiple=-1.0),
        _fact(result="be", r_multiple=0.0),
    ]
    summary = aggregate_statistics(facts)
    assert summary.win_rate == 1 / 3


def test_open_trades_excluded_from_win_rate_and_r_metrics():
    facts = [
        _fact(result="tp", r_multiple=2.0),
        _fact(result=None, r_multiple=None),
    ]
    summary = aggregate_statistics(facts)
    assert (
        summary.win_rate == 1.0
    )  # 1 TP out of 1 *closed* trade -- the open trade isn't in the denominator.
    assert summary.expectancy_r == 2.0
    assert summary.average_r == 2.0


def test_expectancy_equals_average_r():
    facts = [_fact(result="tp", r_multiple=3.0), _fact(result="sl", r_multiple=-1.0)]
    summary = aggregate_statistics(facts)
    assert summary.expectancy_r == summary.average_r == 1.0


def test_profit_factor_is_none_with_zero_gross_loss():
    facts = [_fact(result="tp", r_multiple=2.0), _fact(result="be", r_multiple=0.0)]
    summary = aggregate_statistics(facts)
    assert summary.profit_factor_r is None


def test_profit_factor_divides_gross_profit_by_gross_loss():
    facts = [
        _fact(result="tp", r_multiple=4.0),
        _fact(result="sl", r_multiple=-2.0),
    ]
    summary = aggregate_statistics(facts)
    assert summary.profit_factor_r == 2.0


def test_total_pnl_sums_every_non_deleted_trade_including_open_ones():
    facts = [
        _fact(result="tp", realized_pnl=100.0),
        _fact(result=None, realized_pnl=0.0, r_multiple=None),
    ]
    summary = aggregate_statistics(facts)
    assert summary.total_pnl == 100.0


def test_engine_score_average_skips_none_but_not_zero():
    facts = [
        _fact(confidence_score=100.0),
        _fact(confidence_score=0.0),
        _fact(confidence_score=None),
    ]
    summary = aggregate_statistics(facts)
    # (100 + 0) / 2 = 50 -- the `None` entry contributes nothing to
    # either the sum or the count, but the real `0.0` score still counts.
    assert summary.average_confidence_score == 50.0


def test_aggregate_by_dimension_buckets_null_strategy_as_unassigned():
    strategy_id = uuid.uuid4()
    facts = [
        _fact(strategy_id=strategy_id, r_multiple=2.0),
        _fact(strategy_id=None, r_multiple=-1.0, result="sl"),
    ]
    groups = aggregate_by_dimension(facts, "strategy")
    values = {g.dimension_value for g in groups}
    assert values == {str(strategy_id), UNASSIGNED}


def test_aggregate_by_dimension_direction_never_produces_unassigned():
    facts = [_fact(direction="long"), _fact(direction="short")]
    groups = aggregate_by_dimension(facts, "direction")
    values = {g.dimension_value for g in groups}
    assert values == {"long", "short"}
    assert UNASSIGNED not in values


def test_aggregate_by_dimension_each_group_has_its_own_summary():
    strategy_a = uuid.uuid4()
    strategy_b = uuid.uuid4()
    facts = [
        _fact(strategy_id=strategy_a, result="tp", r_multiple=2.0),
        _fact(strategy_id=strategy_a, result="tp", r_multiple=4.0),
        _fact(strategy_id=strategy_b, result="sl", r_multiple=-1.0),
    ]
    groups = {g.dimension_value: g.summary for g in aggregate_by_dimension(facts, "strategy")}
    assert groups[str(strategy_a)].win_rate == 1.0
    assert groups[str(strategy_a)].average_r == 3.0
    assert groups[str(strategy_b)].win_rate == 0.0
    assert groups[str(strategy_b)].average_r == -1.0


# ---------------------------------------------------------------------
# Rolling Statistics (Sprint 6.2)
# ---------------------------------------------------------------------


def _at(days_ago: int, **overrides):
    return _fact(entered_at=_BASE_TIME - timedelta(days=days_ago), **overrides)


def test_select_rolling_window_keeps_the_most_recent_n_by_entered_at():
    oldest = _at(days_ago=5)
    middle = _at(days_ago=3)
    newest = _at(days_ago=0)
    window = select_rolling_window([oldest, newest, middle], window=2)
    assert window == [newest, middle]


def test_select_rolling_window_with_fewer_facts_than_window_returns_all_of_them():
    facts = [_at(days_ago=2), _at(days_ago=1)]
    window = select_rolling_window(facts, window=10)
    assert len(window) == 2


def test_select_rolling_window_with_no_facts_returns_empty():
    assert select_rolling_window([], window=10) == []


def test_aggregate_rolling_rolling_only_reflects_the_windowed_subset():
    # 2 older SL trades, then 3 newer TP trades -- window=3 must only see
    # the 3 newer TP trades; `overall` must see all 5.
    facts = [
        _at(days_ago=10, result="sl", r_multiple=-1.0),
        _at(days_ago=9, result="sl", r_multiple=-1.0),
        _at(days_ago=2, result="tp", r_multiple=2.0),
        _at(days_ago=1, result="tp", r_multiple=2.0),
        _at(days_ago=0, result="tp", r_multiple=2.0),
    ]
    result = aggregate_rolling(facts, window=3)
    assert result.window == 3
    assert result.rolling.win_rate == 1.0
    assert result.rolling.average_r == 2.0
    assert result.overall.win_rate == 3 / 5
    hand_overall_average_r = (-1.0 + -1.0 + 2.0 + 2.0 + 2.0) / 5
    assert result.overall.average_r == hand_overall_average_r


def test_aggregate_rolling_with_fewer_facts_than_window_rolling_equals_overall():
    facts = [
        _at(days_ago=1, result="tp", r_multiple=1.5),
        _at(days_ago=0, result="sl", r_multiple=-1.0),
    ]
    result = aggregate_rolling(facts, window=200)
    assert result.rolling == result.overall
