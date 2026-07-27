"""
Regression test for the Sprint 3.2 Market Context data-model correction
(see CHANGELOG.md): 28 Market Context criteria were changed from numeric
min/max ranges to a precalculated `category_map`, so `checklist_answers`
can carry the real category label (consistent with every other criterion,
and required for the Bias fan-out to work at all) instead of an
already-converted number.

This is a data *representation* change only — not a behavior change.
Proves it: for every category label, running the real `normalize()`
function with the OLD approach (numeric criterion, fed the real raw
Excel point) and the NEW approach (categorical criterion, fed the real
label) produce the same normalized value.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.seed_configuration import BIAS_CRITERIA, MARKET_CONTEXT_CRITERIA  # noqa: E402

from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.scoring_core import normalize

_BIAS_RAW_CATEGORY_MAPS = {row[0].removeprefix("bias."): row[4] for row in BIAS_CRITERIA}

_CATEGORICAL_MC_ROWS = [row for row in MARKET_CONTEXT_CRITERIA if row[5] is not None]


@pytest.mark.parametrize(
    "mc_id,min_value,max_value,category_map",
    [(row[0], row[3], row[4], row[5]) for row in _CATEGORICAL_MC_ROWS],
)
def test_new_category_map_matches_old_numeric_rescale_for_every_label(
    mc_id, min_value, max_value, category_map
):
    field_and_suffix = mc_id.removeprefix("market_context.")
    raw_points = _BIAS_RAW_CATEGORY_MAPS[field_and_suffix]
    assert set(raw_points) == set(
        category_map
    ), f"{mc_id}: category set mismatch with the real Bias raw points it was derived from"

    old_style_criterion = EvaluationCriterion(
        id=mc_id, name=mc_id, min_value=min_value, max_value=max_value, category_map=None
    )
    new_style_criterion = EvaluationCriterion(
        id=mc_id, name=mc_id, min_value=min_value, max_value=max_value, category_map=category_map
    )

    for label, raw_point in raw_points.items():
        old_result = normalize(old_style_criterion, raw_point)
        new_result = normalize(new_style_criterion, label)
        assert old_result == pytest.approx(new_result, abs=1e-6), (
            f"{mc_id} / '{label}': old (numeric, raw={raw_point}) = {old_result}, "
            f"new (category_map) = {new_result}"
        )


def test_exactly_28_real_fields_were_converted_to_category_map():
    """28 is the exact overlap between Bias's 35 real GROSS_SCORE inputs
    and Market Context's 30 real criteria (macro_events and confluence
    are the only two Market Context criteria Bias doesn't read, and are
    deliberately left numeric -- out of this correction's scope)."""
    converted_fields = {
        row[0].removeprefix("market_context.").removesuffix("_swing")
        for row in _CATEGORICAL_MC_ROWS
    }
    assert len(converted_fields) == 28
    untouched = {row[0] for row in MARKET_CONTEXT_CRITERIA if row[5] is None}
    assert untouched == {"market_context.macro_events", "market_context.confluence"}
