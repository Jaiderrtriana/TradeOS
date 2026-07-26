"""Evaluation domain: EvaluationWeight — Evaluation's own input shape,
mirroring (not importing) `configuration.domain.scoring_weight
.ScoringWeight`'s real columns. See evaluation_criterion.py for why."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationWeight:
    criterion_id: str
    profile_code: str
    weight: float
    is_active: bool = True
