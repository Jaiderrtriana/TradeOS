"""
Shared Kernel — TRADEOS_SYSTEM_ARCHITECTURE.md §3.2: "the one deliberate
exception to 'modules communicate only through contracts'... only these
small, stable value shapes." First real use of this package (Sprint 3.1);
`Score`/`Grade` are named explicitly in that section's list.

TRADEOS_DOMAIN_MODEL.md §9: "Grade — A+/A/B/C/D, always derived from a
Score, never assigned independently." "Score — a 0-100 (or signed, for
Bias) numeric value plus its derived Grade."
"""

from dataclasses import dataclass
from enum import Enum


class Grade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class Score:
    value: float
    # None only for Bias (signed, no `bias_grade` column,
    # TRADEOS_DATABASE_DESIGN.md §6.12) — every other engine (Confidence,
    # Quality, Execution, Market Context) always derives a Grade, per the
    # Sprint 3.2 decision documented in evaluation/domain/grading.py. Not
    # every Score has a Grade, but every Grade has a Score.
    grade: Grade | None = None
