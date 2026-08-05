"""
Trade domain regression tests — TRADEOS_DATABASE_DESIGN.md §6.9's five
computed properties (plus `roi_percent`/`pnl_percent`, new in v2.0),
INV-TRADE-01/02.

The five verification cases mirror exactly
`PROPUESTA_FORMULAS_TRADE_COMPUTED_PROPERTIES.md` §6 (approved,
Sprint 4.1): rows 2 and 3 are real, verified-exact values from
`legacy/Trading Journal v2.0 Stable.xlsx`'s `Trades` sheet (the only two
real trade rows that exist); Cases 3-5 are hand-computed using the same
confirmed formula, covering Short/TP/the `mfe_r == 0` edge case the real
Excel does not contain — each labeled accordingly, per that document.

v2.0 (Trade Entry redesign, Domain Model KDD-07): `status` is now a
required, independent field from `result` (`'open'` retired as a result
value, `result` is `None` until `Closed`) — every `_trade()` call below
states `status` explicitly, matching `validate_status_fields`.
"""

import math
from datetime import datetime, timezone

import pytest

from app.modules.trading.domain.trade import (
    CLOSED,
    LONG,
    OPEN,
    PLANNED,
    SHORT,
    STOP_LOSS,
    TAKE_PROFIT,
    Trade,
    validate_status_fields,
    validate_stop_placement,
)
from app.platform.errors import UnprocessableEntityError

NOW = datetime.now(timezone.utc)


def _trade(**overrides):
    defaults = dict(
        user_id=None,
        market="EURUSD",
        direction=LONG,
        status=OPEN,
        entry_price=100.0,
        stop_loss=95.0,
        entered_at=NOW,
        result=None,
        exit_price=None,
        mfe_price=None,
        mae_price=None,
        closed_at=None,
    )
    defaults.update(overrides)
    return Trade(**defaults)


def _assert_close(actual: float | None, expected: float) -> None:
    assert actual is not None
    assert math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)


# --- Real Excel row 2 (Long, SL) ---------------------------------------


def test_real_row_2_r_multiple():
    trade = _trade(
        direction=LONG,
        status=CLOSED,
        entry_price=1788.48,
        stop_loss=1764.3,
        exit_price=1763.45,
        result=STOP_LOSS,
        mfe_price=1799.02,
        mae_price=1763.08,
        closed_at=NOW,
    )
    _assert_close(trade.r_multiple, -1.035153019)
    _assert_close(trade.mfe_r, 0.4358974359)
    _assert_close(trade.mae_r, 1.050454921)
    assert trade.captured_pct is None  # result != tp
    _assert_close(trade.potential_left_r, 0.4358974359)


def test_real_row_3_r_multiple():
    trade = _trade(
        direction=LONG,
        status=CLOSED,
        entry_price=63069.8,
        stop_loss=62120.0,
        exit_price=62060.7,
        result=STOP_LOSS,
        mfe_price=64230.0,
        mae_price=62100.0,
        closed_at=NOW,
    )
    _assert_close(trade.r_multiple, -1.062434197)
    _assert_close(trade.mfe_r, 1.22152032)
    _assert_close(trade.mae_r, 1.021057065)
    assert trade.captured_pct is None
    _assert_close(trade.potential_left_r, 1.22152032)


# --- Hand-computed cases (Short/TP/mfe_r==0 edge case not in real data) ---


def test_case_3_short_loser():
    trade = _trade(
        direction=SHORT,
        status=CLOSED,
        entry_price=100,
        stop_loss=105,
        exit_price=102,
        result=STOP_LOSS,
        mfe_price=99,
        mae_price=104,
        closed_at=NOW,
    )
    _assert_close(trade.r_multiple, -0.4)
    _assert_close(trade.mfe_r, 0.2)
    _assert_close(trade.mae_r, 0.8)
    assert trade.captured_pct is None
    _assert_close(trade.potential_left_r, 0.2)


def test_case_4_long_winner_tp_exercises_captured_pct_numeric_branch():
    trade = _trade(
        direction=LONG,
        status=CLOSED,
        entry_price=100,
        stop_loss=95,
        exit_price=108,
        result=TAKE_PROFIT,
        mfe_price=110,
        mae_price=97,
        closed_at=NOW,
    )
    _assert_close(trade.r_multiple, 1.6)
    _assert_close(trade.mfe_r, 2.0)
    _assert_close(trade.mae_r, 0.6)
    _assert_close(trade.captured_pct, 0.8)  # raw ratio, never scaled to 80.0
    _assert_close(trade.potential_left_r, 0.4)


def test_case_5_mfe_r_zero_edge_case_distinguishes_captured_pct_from_potential_left_r():
    """The one case that proves captured_pct and potential_left_r do NOT
    share the same 'blank' condition: mfe_r == 0 nulls captured_pct but
    potential_left_r still computes a real number (0.0) — real Excel
    behavior, deliberately not unified for consistency (per approved
    decision, Sprint 4.1)."""
    trade = _trade(
        direction=LONG,
        status=CLOSED,
        entry_price=100,
        stop_loss=95,
        exit_price=90,
        result=STOP_LOSS,
        mfe_price=100,  # never moved favorably -> mfe_r == 0
        mae_price=88,
        closed_at=NOW,
    )
    _assert_close(trade.r_multiple, -2.0)
    _assert_close(trade.mfe_r, 0.0)
    _assert_close(trade.mae_r, 2.4)
    assert trade.captured_pct is None  # mfe_r == 0 -> null, regardless of result
    _assert_close(trade.potential_left_r, 0.0)  # still a real number, not null


# --- Properties with no data at all -------------------------------------


def test_open_trade_has_no_computable_result_properties():
    trade = _trade(status=OPEN, result=None, exit_price=None, closed_at=None)
    assert trade.r_multiple is None  # exit_price absent
    assert trade.mfe_r is None  # mfe_price absent (default)
    assert trade.mae_r is None  # mae_price absent (default)
    assert trade.captured_pct is None
    assert trade.potential_left_r is None


def test_planned_trade_has_no_computable_properties():
    trade = _trade(status=PLANNED, entry_price=None, stop_loss=None, entered_at=None, result=None)
    assert trade.r_multiple is None
    assert trade.mfe_r is None
    assert trade.mae_r is None
    assert trade.captured_pct is None
    assert trade.potential_left_r is None
    assert trade.roi_percent is None
    assert trade.pnl_percent is None


# --- roi_percent / pnl_percent (new in v2.0, DI-14 — never stored) ------


def test_roi_percent_and_pnl_percent_computed_from_realized_pnl_margin_leverage():
    trade = _trade(
        status=CLOSED,
        entry_price=100,
        stop_loss=95,
        exit_price=108,
        result=TAKE_PROFIT,
        closed_at=NOW,
        margin_used=200.0,
        realized_pnl=100.0,
        leverage="10X",
    )
    _assert_close(trade.roi_percent, 0.5)
    _assert_close(trade.pnl_percent, 0.05)


def test_roi_percent_none_without_margin_used():
    trade = _trade(
        status=CLOSED,
        entry_price=100,
        stop_loss=95,
        exit_price=108,
        result=TAKE_PROFIT,
        closed_at=NOW,
        margin_used=None,
        realized_pnl=100.0,
    )
    assert trade.roi_percent is None
    assert trade.pnl_percent is None


# --- INV-TRADE-01: stop placement ---------------------------------------


def test_inv_trade_01_rejects_long_stop_above_entry():
    with pytest.raises(UnprocessableEntityError):
        validate_stop_placement(LONG, entry_price=100, stop_loss=105)


def test_inv_trade_01_rejects_short_stop_below_entry():
    with pytest.raises(UnprocessableEntityError):
        validate_stop_placement(SHORT, entry_price=100, stop_loss=95)


def test_inv_trade_01_accepts_valid_long_placement():
    validate_stop_placement(LONG, entry_price=100, stop_loss=95)


def test_inv_trade_01_enforced_on_trade_construction():
    with pytest.raises(UnprocessableEntityError):
        _trade(direction=LONG, entry_price=100, stop_loss=105)


# --- INV-TRADE-02: which fields exist per status (v2.0, redefined) ------


def test_inv_trade_02_rejects_closed_without_exit_price():
    with pytest.raises(UnprocessableEntityError):
        validate_status_fields(
            CLOSED,
            entry_price=100,
            entered_at=NOW,
            exit_price=None,
            closed_at=NOW,
            result=STOP_LOSS,
        )


def test_inv_trade_02_rejects_open_with_result_set():
    with pytest.raises(UnprocessableEntityError):
        validate_status_fields(
            OPEN,
            entry_price=100,
            entered_at=NOW,
            exit_price=102,
            closed_at=None,
            result=STOP_LOSS,
        )


def test_inv_trade_02_rejects_closed_without_closed_at():
    with pytest.raises(UnprocessableEntityError):
        validate_status_fields(
            CLOSED,
            entry_price=100,
            entered_at=NOW,
            exit_price=102,
            closed_at=None,
            result=STOP_LOSS,
        )


def test_inv_trade_02_accepts_open_with_only_entry_facts():
    validate_status_fields(
        OPEN, entry_price=100, entered_at=NOW, exit_price=None, closed_at=None, result=None
    )


def test_inv_trade_02_accepts_closed_with_everything_supplied():
    validate_status_fields(
        CLOSED,
        entry_price=100,
        entered_at=NOW,
        exit_price=102,
        closed_at=NOW,
        result=STOP_LOSS,
    )


def test_inv_trade_02_accepts_planned_with_nothing_supplied():
    validate_status_fields(
        PLANNED, entry_price=None, entered_at=None, exit_price=None, closed_at=None, result=None
    )


def test_inv_trade_02_rejects_planned_with_entry_price_set():
    with pytest.raises(UnprocessableEntityError):
        validate_status_fields(
            PLANNED,
            entry_price=100,
            entered_at=None,
            exit_price=None,
            closed_at=None,
            result=None,
        )


def test_inv_trade_02_enforced_on_trade_construction():
    with pytest.raises(UnprocessableEntityError):
        _trade(status=CLOSED, result=STOP_LOSS, exit_price=None, closed_at=None)
