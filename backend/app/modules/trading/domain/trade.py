"""
Trading domain: Trade — Aggregate Root (TRADEOS_DOMAIN_MODEL.md §8.1, v2.0).

v2.0 (Domain Model KDD-07): `TradeStatus` (`planned`/`open`/`closed`) is
now independent of `TradeResult` (`tp`/`sl`/`be`, `None` while not
closed — `'open'` retired as a result value). `entry_price`/`stop_loss`/
`entered_at` are optional (absent while `status=planned`). `take_profit`/
`margin_used` are new owned fields. `roi_percent`/`pnl_percent` are new
computed properties, alongside the pre-existing `r_multiple`/`mfe_r`/
`mae_r`/`captured_pct`/`potential_left_r` — none of the six are ever
stored (`TRADEOS_DATABASE_DESIGN.md` §6.9).

Computed properties are implemented here as read-only properties, never
stored — exact formulas extracted from and verified against
`legacy/Trading Journal v2.0 Stable.xlsx`'s real `📒 Trades`/`📒 Trades
simple` sheets (session-scoped review documents
`PROPUESTA_FORMULAS_TRADE_COMPUTED_PROPERTIES.md`, Sprint 4.1, and the
Trade Entry redesign review, v2.0 — see CHANGELOG.md for both).

Approved representation decisions (editorial choices for the API
contract, not Excel behavior):
- `captured_pct` collapses the real Excel's three states (a number only
  for TP trades, the literal text "—" for non-TP, blank for no/zero MFE)
  into two: a float, or `None`. The distinction between "not applicable"
  (non-TP) and "no data" (blank) is a *display* artifact of the
  spreadsheet, not a business difference — both become `None` here.
- `captured_pct` returns the raw ratio (`0.8`), never a pre-multiplied
  percentage (`80.0`) — matches the Excel's own stored value exactly
  (its cell `number_format` is `"General"`, not `"0%"`). The frontend is
  responsible for any percentage formatting. `roi_percent`/`pnl_percent`
  follow the identical raw-ratio convention.

Deliberately **not** unified: `captured_pct` treats `mfe_r == 0` as "no
data" (`None`); `potential_left_r` does **not** — it only returns `None`
when `mfe_r` is genuinely absent (`mfe_price` was never supplied). This
is the real, verified Excel behavior (the two real formulas use
different blank conditions) and is preserved exactly, not smoothed into
one shared rule for the sake of symmetry.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.platform.errors import UnprocessableEntityError

LONG = "long"
SHORT = "short"
DIRECTIONS = (LONG, SHORT)

PLANNED = "planned"
OPEN = "open"
CLOSED = "closed"
STATUSES = (PLANNED, OPEN, CLOSED)

TAKE_PROFIT = "tp"
STOP_LOSS = "sl"
BREAK_EVEN = "be"
RESULTS = (TAKE_PROFIT, STOP_LOSS, BREAK_EVEN)


def validate_stop_placement(
    direction: str, entry_price: float | None, stop_loss: float | None
) -> None:
    """INV-TRADE-01 (`TRADEOS_DOMAIN_MODEL.md` §15, realizes DI-02): Long
    stop must be below entry; Short stop must be above entry. Only
    checked once both exist — `stop_loss` remains optional at every
    status (v2.0), and `entry_price` is absent entirely for `Planned`
    Trades."""
    if entry_price is None or stop_loss is None:
        return
    if direction == LONG and not stop_loss < entry_price:
        raise UnprocessableEntityError("For a Long trade, stop_loss must be below entry_price.")
    if direction == SHORT and not stop_loss > entry_price:
        raise UnprocessableEntityError("For a Short trade, stop_loss must be above entry_price.")


def validate_status_fields(
    status: str,
    entry_price: float | None,
    entered_at: datetime | None,
    exit_price: float | None,
    closed_at: datetime | None,
    result: str | None,
) -> None:
    """INV-TRADE-02, redefined v2.0 (`TRADEOS_DOMAIN_MODEL.md` §15,
    realizes DI-01): exactly which facts exist is determined by
    `status`, never independently. `stop_loss`/`take_profit`/
    `margin_used` are never part of this check — all three remain
    optional at every status (Domain Model §8.1, approved v2.0 review)."""
    if status == PLANNED:
        if entry_price is not None or entered_at is not None:
            raise UnprocessableEntityError(
                "A planned trade must not have entry_price or entered_at."
            )
        if exit_price is not None or closed_at is not None or result is not None:
            raise UnprocessableEntityError(
                "A planned trade must not have exit_price, closed_at, or result."
            )
    elif status == OPEN:
        if entry_price is None or entered_at is None:
            raise UnprocessableEntityError("An open trade requires entry_price and entered_at.")
        if exit_price is not None or closed_at is not None or result is not None:
            raise UnprocessableEntityError(
                "An open trade must not have exit_price, closed_at, or result."
            )
    else:
        if entry_price is None or entered_at is None:
            raise UnprocessableEntityError("A closed trade requires entry_price and entered_at.")
        if exit_price is None or closed_at is None or result is None:
            raise UnprocessableEntityError(
                "Closing a trade requires result, exit_price, and closed_at together."
            )


def compute_r_multiple(
    direction: str,
    entry_price: float | None,
    stop_loss: float | None,
    exit_price: float | None,
) -> float | None:
    """Real Excel formula (column X, "R:R real"):
    `=IFERROR(IF(F2="Long",(R2-N2)/(N2-O2),(N2-R2)/(O2-N2)),"")`

    Extracted as a standalone function (Sprint 5.2) so
    `MistakePriorityRankingService` can compute a mistake's aggregate
    cost directly from raw joined query fields (`TradeMistakeRepository.
    list_trade_facts_for_ranking`) without constructing a full `Trade`
    domain object per row — the same formula, reused rather than
    duplicated. `Trade.r_multiple` below is now a thin wrapper over this.
    `entry_price`/`stop_loss` became optional in v2.0 (a `Planned`
    Trade has neither) — `None` for either is treated the same as a
    missing `exit_price` always was: not yet computable.
    """
    if entry_price is None or stop_loss is None or exit_price is None:
        return None
    try:
        if direction == LONG:
            return (exit_price - entry_price) / (entry_price - stop_loss)
        return (entry_price - exit_price) / (stop_loss - entry_price)
    except ZeroDivisionError:
        return None


def _parse_leverage_multiplier(leverage: str) -> float | None:
    """`"15X"` -> `15.0`. `None` for empty/unparseable input — mirrors
    the Excel's own `VALUE(SUBSTITUTE(G2,"X",""))` failing silently via
    `IFERROR` when `Leverage` is blank."""
    if not leverage:
        return None
    try:
        return float(leverage.upper().replace("X", "").strip())
    except ValueError:
        return None


@dataclass
class Trade:
    user_id: uuid.UUID
    market: str
    direction: str
    status: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    strategy_id: uuid.UUID | None = None
    setup_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    entry_trigger_id: uuid.UUID | None = None
    exit_price: float | None = None
    size: float = 0
    margin_used: float | None = None
    leverage: str = ""
    result: str | None = None
    realized_pnl: float = 0
    mfe_price: float | None = None
    mae_price: float | None = None
    notes: str = ""
    entered_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
    created_by_user_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        validate_stop_placement(self.direction, self.entry_price, self.stop_loss)
        validate_status_fields(
            self.status,
            self.entry_price,
            self.entered_at,
            self.exit_price,
            self.closed_at,
            self.result,
        )

    @property
    def r_multiple(self) -> float | None:
        """Real Excel formula (column X, "R:R real"):
        `=IFERROR(IF(F2="Long",(R2-N2)/(N2-O2),(N2-R2)/(O2-N2)),"")`"""
        return compute_r_multiple(self.direction, self.entry_price, self.stop_loss, self.exit_price)

    @property
    def mfe_r(self) -> float | None:
        """Real Excel formula (column BB, "MFE (R)"):
        `=IF(OR(AZ2="",N2="",O2=""),"",IF(F2="Long",(AZ2-N2)/ABS(N2-O2),(N2-AZ2)/ABS(N2-O2)))`"""
        if self.mfe_price is None or self.entry_price is None or self.stop_loss is None:
            return None
        risk = abs(self.entry_price - self.stop_loss)
        if self.direction == LONG:
            return (self.mfe_price - self.entry_price) / risk
        return (self.entry_price - self.mfe_price) / risk

    @property
    def mae_r(self) -> float | None:
        """Real Excel formula (column BC, "MAE (R)"):
        `=IF(OR(BA2="",N2="",O2=""),"",IF(F2="Long",(N2-BA2)/ABS(N2-O2),(BA2-N2)/ABS(N2-O2)))`"""
        if self.mae_price is None or self.entry_price is None or self.stop_loss is None:
            return None
        risk = abs(self.entry_price - self.stop_loss)
        if self.direction == LONG:
            return (self.entry_price - self.mae_price) / risk
        return (self.mae_price - self.entry_price) / risk

    @property
    def captured_pct(self) -> float | None:
        """Real Excel formula (column BD, "% Capturado"):
        `=IF(OR(BB2="",BB2=0),"",IF(S2="TP",IFERROR(X2/BB2,""),"—"))`
        — `None` for a blank `mfe_r`, a zero `mfe_r`, *and* any non-TP
        result (the real Excel's "—" collapses into `None` too — see
        module docstring's approved representation decision)."""
        mfe_r = self.mfe_r
        if mfe_r is None or mfe_r == 0:
            return None
        if self.result != TAKE_PROFIT:
            return None
        r_multiple = self.r_multiple
        if r_multiple is None:
            return None
        return r_multiple / mfe_r

    @property
    def potential_left_r(self) -> float | None:
        """Real Excel formula (column BE, "Potencial Restante (R)"):
        `=IF(BB2="","",BB2-MAX(0,IF(X2="",0,X2)))` — blank *only* when
        `mfe_r` itself is absent, deliberately **not** when it's `0`
        (unlike `captured_pct` above) — this is the real Excel's own
        behavior, preserved exactly, not unified for symmetry."""
        mfe_r = self.mfe_r
        if mfe_r is None:
            return None
        r_multiple = self.r_multiple
        return mfe_r - max(0.0, r_multiple if r_multiple is not None else 0.0)

    @property
    def roi_percent(self) -> float | None:
        """`ROI = realized_pnl / margin_used` — never stored (Domain
        Model DI-14, KDD-07). `None` when `margin_used` is absent or
        zero (division not meaningful)."""
        if self.margin_used is None or self.margin_used == 0:
            return None
        return self.realized_pnl / self.margin_used

    @property
    def pnl_percent(self) -> float | None:
        """Real Excel formula (column Q of `📒 Trades simple`, "P&L
        (%)"): `=IF(OR(P2="",G2=""),"",P2/VALUE(SUBSTITUTE(G2,"X","")))`
        — `P&L % = ROI / Leverage`, the Excel's own literal formula,
        preserved exactly. Never stored (Domain Model DI-14, KDD-07)."""
        roi_percent = self.roi_percent
        if roi_percent is None:
            return None
        leverage_multiplier = _parse_leverage_multiplier(self.leverage)
        if leverage_multiplier is None or leverage_multiplier == 0:
            return None
        return roi_percent / leverage_multiplier
