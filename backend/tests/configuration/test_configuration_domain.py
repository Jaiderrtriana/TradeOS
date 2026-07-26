import uuid

from app.modules.configuration.domain.engine_type import EngineType
from app.modules.configuration.domain.scoring_configuration_version import (
    DRAFT,
    ScoringConfigurationVersion,
)
from app.modules.configuration.domain.scoring_criterion import ScoringCriterion
from app.modules.configuration.domain.scoring_weight import ScoringWeight


def test_engine_type_defaults_to_active():
    engine_type = EngineType(code="confidence", display_name="Trade Confidence", is_signed=False)
    assert engine_type.is_active is True


def test_bias_is_the_one_signed_engine_type():
    """Domain Invariant DI-05: exactly one engine type is signed."""
    bias = EngineType(code="bias", display_name="Bias Index", is_signed=True)
    assert bias.is_signed is True


def test_new_configuration_version_starts_as_draft():
    """Domain Invariant DI-06/DI-07: versions are created as drafts, never
    directly published."""
    version = ScoringConfigurationVersion(version_label="v1.0")
    assert version.status == DRAFT
    assert version.published_at is None


def test_each_criterion_gets_its_own_category_map_instance():
    """Mutable default must not be shared across instances."""
    first = ScoringCriterion(
        id="confidence.htf_alignment",
        engine_type_code="confidence",
        name="HTF Alignment",
        source_field="htf_alignment",
        min_value=0,
        max_value=100,
        category_map={"Full Alignment": 100},
    )
    second = ScoringCriterion(
        id="confidence.emotional_state",
        engine_type_code="confidence",
        name="Emotional State",
        source_field="emotional_state",
        min_value=0,
        max_value=100,
    )
    assert second.category_map is None
    first.category_map["Moderate Alignment"] = 70
    assert second.category_map is None


def test_scoring_weight_defaults_to_active():
    weight = ScoringWeight(
        configuration_version_id=uuid.uuid4(),
        criterion_id="confidence.htf_alignment",
        profile_code="day_trading",
        weight=0.2,
    )
    assert weight.is_active is True
