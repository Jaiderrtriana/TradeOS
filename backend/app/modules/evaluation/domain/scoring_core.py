"""
The generic weighted-scoring core — TRADEOS_DOMAIN_MODEL.md §12.1:
"the EvaluationEngine... a pure function of its inputs." PROJECT_AUDIT.md
§3.2: "el Evaluation Engine es genérico: una clase de cálculo (criterios +
pesos + perfil -> score ponderado, autonormalizado dividiendo por la suma
de pesos activos)... instanciada 5 veces." This module is that one
calculation, meant to be reused by every engine (Confidence and Quality
this sprint; Execution/Market Context/Bias in Sprint 3.2) — it carries no
assumption specific to any single engine (no rounding, no grading, no
per-criterion value transforms — those are each engine's own concern, see
confidence_engine.py/quality_engine.py/grading.py).

Deliberately excludes Bias's signed normalization (Domain Invariant DI-05)
and any per-profile weight-selection nuance beyond exact `profile_code`
matching — out of this sprint's approved scope (Sprint 3.2 owns Bias).
"""

from app.modules.evaluation.domain.criterion_breakdown_row import CriterionBreakdownRow
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight


def normalize(criterion: EvaluationCriterion, raw_value: str | float) -> float:
    """A criterion's raw answer -> a 0-100 normalized value.

    Categorical criteria (`category_map` set) are looked up directly.
    Numeric criteria are linearly rescaled from
    [`min_value`, `max_value`] to [0, 100]
    (TRADEOS_DATABASE_DESIGN.md §6.5: "its expected numeric range") — the
    identity mapping when `min_value=0, max_value=100`, which is exactly
    Confidence's `bias_index_at_entry` today, and the real formula Market
    Context's non-identity ranges (e.g. `DXY`, -4..4) will need in
    Sprint 3.2, prepared now per your approval rather than redesigned
    later.
    """
    if criterion.category_map is not None:
        return float(criterion.category_map[str(raw_value)])

    raw_number = float(raw_value)
    value_range = criterion.max_value - criterion.min_value
    if value_range == 0:
        return 0.0
    return (raw_number - criterion.min_value) / value_range * 100


def compute_weighted_score(
    criteria: list[EvaluationCriterion],
    weights: list[EvaluationWeight],
    answers: dict[str, str | float],
    profile_code: str,
) -> tuple[float, list[CriterionBreakdownRow]]:
    """Weighted average of every active, answered criterion for the given
    profile, plus its full per-criterion breakdown (Domain Invariant
    DI-08). Divides by the sum of *active* weights only
    (INV-WEIGHT-01) — never a fixed constant, so a deactivated weight (or
    a criterion with no supplied answer, handled gracefully rather than
    erroring, per TRADEOS_BACKEND_BLUEPRINT.md §4.1) simply drops out of
    both the numerator and the denominator.
    """
    criteria_by_id = {criterion.id: criterion for criterion in criteria}
    breakdown: list[CriterionBreakdownRow] = []
    total_weight = 0.0
    total_contribution = 0.0

    for weight in weights:
        if not weight.is_active or weight.profile_code != profile_code:
            continue
        criterion = criteria_by_id.get(weight.criterion_id)
        if criterion is None:
            continue
        if weight.criterion_id not in answers:
            continue

        raw_value = answers[weight.criterion_id]
        normalized_value = normalize(criterion, raw_value)
        contribution = normalized_value * weight.weight

        total_weight += weight.weight
        total_contribution += contribution
        breakdown.append(
            CriterionBreakdownRow(
                criterion_id=criterion.id,
                criterion_name=criterion.name,
                raw_value=str(raw_value),
                normalized_value=normalized_value,
                weight=weight.weight,
                contribution=contribution,
            )
        )

    if total_weight == 0:
        return 0.0, breakdown
    return total_contribution / total_weight, breakdown
