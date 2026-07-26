"""
`round_half_up` — TRADEOS_BACKEND_BLUEPRINT.md §15: "the historical
`round_half_up` rounding defect found and fixed during the reference
implementation's own construction," permanently regression-tested per
Sprint 3.1's Deliverable.

Python's built-in `round()` uses round-half-to-even ("banker's rounding");
Excel's `ROUND()` — which every real Confidence/Quality formula in
`legacy/Trading Journal v2.0 Stable.xlsx` uses — rounds half away from
zero. They silently disagree exactly on `.5` boundaries: confirmed with a
real trade row from that Excel file (Confidence's raw weighted score is
48.5; Excel's `ROUND(48.5, 0)` is 49, Python's `round(48.5)` is 48, since
48 is even). Using `Decimal` with `ROUND_HALF_UP` reproduces Excel's
behavior exactly, independent of Python's default.
"""

from decimal import ROUND_HALF_UP, Decimal


def round_half_up(value: float, ndigits: int = 0) -> float:
    # Decimal(str(value)), not Decimal(value) directly — avoids importing
    # the raw float's binary-representation artifacts into the rounding
    # decision.
    quantum = Decimal("1").scaleb(-ndigits)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))
