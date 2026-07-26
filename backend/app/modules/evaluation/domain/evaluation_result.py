"""
EvaluationResult — the combined shape of all five engines' outputs,
mirroring TRADEOS_API_SPECIFICATION.md §6.5's documented response shape
for both `POST /evaluation/preview` and `GET /trades/{id}/evaluation`:
`{"confidence": {"score",...,"grade",...,"breakdown"}, ..., "bias":
{"score", "breakdown"}}` (no `grade` key under `bias`).

Not a `shared_kernel` type (TRADEOS_SYSTEM_ARCHITECTURE.md §3.2 does not
name it) and not imported from anywhere else — it is Evaluation's own
domain-layer shape, mirroring (never importing) the eventual
`trading.evaluation_snapshots` table Trading will own in Phase 4.
"""

from dataclasses import dataclass

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.shared_kernel.value_objects import Score


@dataclass(frozen=True)
class EngineInput:
    """One engine's own criteria/weights — the generic core is
    "instantiated five times" (`PROJECT_AUDIT.md` §3.2), each with its own
    independent input, never a shared/mixed list."""

    criteria: list[EvaluationCriterion]
    weights: list[EvaluationWeight]


@dataclass(frozen=True)
class EngineResult:
    score: Score
    breakdown: list[CriterionBreakdownRow]


@dataclass(frozen=True)
class EvaluationResult:
    confidence: EngineResult
    quality: EngineResult
    execution: EngineResult
    market_context: EngineResult
    bias: EngineResult
