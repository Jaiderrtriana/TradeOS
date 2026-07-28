"""
Trading domain: EvaluationSnapshot / EvaluationSnapshotBreakdown —
`TRADEOS_DATABASE_DESIGN.md` §6.11-6.13, `TRADEOS_DOMAIN_MODEL.md` §8.3.

Trading's own shape, mirroring — never importing — Evaluation's
`EvaluationResult`/`EngineResult`/`CriterionBreakdownRow`
(`app/modules/evaluation/domain/evaluation_result.py` and
`criterion_breakdown_row.py` both already document this exact mirroring
relationship, anticipated back in Sprint 3.2 for this module).

Flattened per engine (`confidence_score`/`confidence_grade`, ...) rather
than nested, matching the `evaluation_snapshots` table's own columns —
`bias_score` has no paired grade column (Bias is signed, ungraded, same
as `Score.grade` being `None` for Bias in Evaluation's own domain).

"Exactly one *current* snapshot per Trade" (§6.12) is enforced by the
migration's partial unique index
(`ix_evaluation_snapshots_one_current_per_trade`), not re-validated here
— this dataclass only carries `is_current`, it does not police it.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class EvaluationSnapshotBreakdown:
    criterion_id: str
    engine_type_code: str
    criterion_name_at_time: str
    raw_value: str
    normalized_value: float
    weight: float
    contribution: float


@dataclass
class EvaluationSnapshot:
    trade_id: uuid.UUID
    configuration_version_id: uuid.UUID
    confidence_score: float | None
    confidence_grade: str | None
    quality_score: float | None
    quality_grade: str | None
    execution_score: float | None
    execution_grade: str | None
    market_context_score: float | None
    market_context_grade: str | None
    bias_score: float | None
    breakdowns: list[EvaluationSnapshotBreakdown]
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    is_current: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
