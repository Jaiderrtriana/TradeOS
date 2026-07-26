"""
Evaluation domain: CriterionBreakdownRow — TRADEOS_DOMAIN_MODEL.md §9:
"one line of a Score's explanation: criterion name, raw value, normalized
value, weight, contribution. Exists only inside an EvaluationSnapshot."
Not a shared_kernel type (TRADEOS_SYSTEM_ARCHITECTURE.md §3.2 does not
name it) — it belongs here, in Evaluation's own domain layer, mirroring
`trading.evaluation_snapshot_breakdowns`'s shape (owned by Trading once
that module exists, Phase 4) without importing anything from it.

`raw_value` is a string, matching `TRADEOS_DATABASE_DESIGN.md` §6.13's
`raw_value TEXT NOT NULL` ("stored as text because a raw value may be
numeric or categorical").
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CriterionBreakdownRow:
    criterion_id: str
    criterion_name: str
    raw_value: str
    normalized_value: float
    weight: float
    contribution: float
