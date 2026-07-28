"""
Trading domain: Trade — Aggregate Root (TRADEOS_DOMAIN_MODEL.md §8.1).

Computed properties (`r_multiple`, `mfe_r`, `mae_r`, `captured_pct`,
`potential_left_r`) are implemented here as read-only properties, never
stored (`TRADEOS_DATABASE_DESIGN.md` §6.9) — exact formulas extracted
from and verified against `legacy/Trading Journal v2.0 Stable.xlsx`'s
real `📒 Trades` sheet columns X/BB/BC/BD/BE (session-scoped review
document `PROPUESTA_FORMULAS_TRADE_COMPUTED_PROPERTIES.md`, approved
before this file was written — see CHANGELOG.md, Sprint 4.1, for the
full derivation and the two approved representation decisions below).

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
  responsible for any percentage formatting.

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

OPEN = "open"
TAKE_PROFIT = "tp"
STOP_LOSS = "sl"
BREAK_EVEN = "be"
RESULTS = (OPEN, TAKE_PROFIT, STOP_LOSS, BREAK_EVEN)


def validate_stop_placement(direction: str, entry_price: float, stop_loss: float) -> None:
    """INV-TRADE-01 (`TRADEOS_DOMAIN_MODEL.md` §15, realizes DI-02): Long
    stop must be below entry; Short stop must be above entry."""
    if direction == LONG and not stop_loss < entry_price:
        raise UnprocessableEntityError("For a Long trade, stop_loss must be below entry_price.")
    if direction == SHORT and not stop_loss > entry_price:
        raise UnprocessableEntityError("For a Short trade, stop_loss must be above entry_price.")


def validate_close_requires_result_and_exit_price(
    result: str, exit_price: float | None, closed_at: datetime | None
) -> None:
    """INV-TRADE-02 (`TRADEOS_DOMAIN_MODEL.md` §15, realizes DI-01):
    closing requires `result` + `exit_price` together — never one without
    the other. `closed_at` is included in the same check because it is
    the server-assigned counterpart of the same fact (see module
    docstring's `closed_at` note; `TRADEOS_DATABASE_DESIGN.md` §6.9's
    check constraint covers all three together)."""
    if result == OPEN:
        if exit_price is not None or closed_at is not None:
            raise UnprocessableEntityError(
                "An open trade must not have exit_price or a close timestamp."
            )
    else:
        if exit_price is None or closed_at is None:
            raise UnprocessableEntityError(
                "Closing a trade requires result and exit_price together."
            )


@dataclass
class Trade:
    user_id: uuid.UUID
    market: str
    direction: str
    entry_price: float
    stop_loss: float
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    strategy_id: uuid.UUID | None = None
    setup_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    entry_trigger_id: uuid.UUID | None = None
    exit_price: float | None = None
    size: float = 0
    leverage: str = ""
    result: str = OPEN
    realized_pnl: float = 0
    mfe_price: float | None = None
    mae_price: float | None = None
    notes: str = ""
    entered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: datetime | None = None
    created_by_user_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        validate_stop_placement(self.direction, self.entry_price, self.stop_loss)
        validate_close_requires_result_and_exit_price(self.result, self.exit_price, self.closed_at)

    @property
    def r_multiple(self) -> float | None:
        """Real Excel formula (column X, "R:R real"):
        `=IFERROR(IF(F2="Long",(R2-N2)/(N2-O2),(N2-R2)/(O2-N2)),"")`"""
        if self.exit_price is None:
            return None
        try:
            if self.direction == LONG:
                return (self.exit_price - self.entry_price) / (self.entry_price - self.stop_loss)
            return (self.entry_price - self.exit_price) / (self.stop_loss - self.entry_price)
        except ZeroDivisionError:
            return None

    @property
    def mfe_r(self) -> float | None:
        """Real Excel formula (column BB, "MFE (R)"):
        `=IF(OR(AZ2="",N2="",O2=""),"",IF(F2="Long",(AZ2-N2)/ABS(N2-O2),(N2-AZ2)/ABS(N2-O2)))`"""
        if self.mfe_price is None:
            return None
        risk = abs(self.entry_price - self.stop_loss)
        if self.direction == LONG:
            return (self.mfe_price - self.entry_price) / risk
        return (self.entry_price - self.mfe_price) / risk

    @property
    def mae_r(self) -> float | None:
        """Real Excel formula (column BC, "MAE (R)"):
        `=IF(OR(BA2="",N2="",O2=""),"",IF(F2="Long",(N2-BA2)/ABS(N2-O2),(BA2-N2)/ABS(N2-O2)))`"""
        if self.mae_price is None:
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
