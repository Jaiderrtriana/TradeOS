"""
The `EvaluationEngine` orchestrator — TRADEOS_DOMAIN_MODEL.md §12.1:
"produces an EvaluationSnapshot... a pure function of its inputs."
Composes the five independent engines (each already a thin, tested caller
of `scoring_core.compute_weighted_score`) into one combined result.
Deferred from Sprint 3.1 specifically because it needed all five engines
to exist first (`TRADEOS_IMPLEMENTATION_MASTER_PLAN.md` Sprint 3.2:
"Deliverables: all five engines complete").

Still zero infrastructure dependencies: every `EngineInput` is supplied by
the caller (the Application layer, `PreviewEvaluationUseCase`), never
fetched here.
"""

from app.modules.evaluation.domain.bias_engine import score_bias
from app.modules.evaluation.domain.confidence_engine import score_confidence
from app.modules.evaluation.domain.evaluation_result import (
    EngineInput,
    EngineResult,
    EvaluationResult,
)
from app.modules.evaluation.domain.execution_engine import score_execution
from app.modules.evaluation.domain.market_context_engine import score_market_context
from app.modules.evaluation.domain.quality_engine import score_quality


def evaluate(
    confidence: EngineInput,
    quality: EngineInput,
    execution: EngineInput,
    market_context: EngineInput,
    bias: EngineInput,
    answers: dict[str, str | float],
    profile_code: str,
) -> EvaluationResult:
    confidence_score, confidence_breakdown = score_confidence(
        confidence.criteria, confidence.weights, answers, profile_code
    )
    quality_score, quality_breakdown = score_quality(
        quality.criteria, quality.weights, answers, profile_code
    )
    execution_score, execution_breakdown = score_execution(
        execution.criteria, execution.weights, answers, profile_code
    )
    market_context_score, market_context_breakdown = score_market_context(
        market_context.criteria, market_context.weights, answers, profile_code
    )
    bias_score, bias_breakdown = score_bias(bias.criteria, bias.weights, answers, profile_code)

    return EvaluationResult(
        confidence=EngineResult(confidence_score, confidence_breakdown),
        quality=EngineResult(quality_score, quality_breakdown),
        execution=EngineResult(execution_score, execution_breakdown),
        market_context=EngineResult(market_context_score, market_context_breakdown),
        bias=EngineResult(bias_score, bias_breakdown),
    )
