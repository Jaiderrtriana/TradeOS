"""
PreviewEvaluationUseCase — TRADEOS_API_SPECIFICATION.md §6.5,
POST /evaluation/preview.

Per TRADEOS_BACKEND_BLUEPRINT.md §4.5's PreviewEvaluation description:
a pure computation, no persistence, no transaction, no event.

Owns the one translation step the user explicitly scoped to this layer
only: `checklist_answers` arrives keyed by a criterion's `source_field`
(API Specification line 190) but Sprint 3.1's domain engines work
exclusively with the stable `criterion_id` (TRADEOS_DOMAIN_MODEL.md
INV-CRITERION-01). That translation happens here, once, and the already
-shipped domain layer is never touched.

The translation is a fan-out (one `source_field` -> many `criterion_id`s),
not a 1:1 map: the real Excel's Bias Index formula reads the exact same
raw checklist fields (`dxy`, `spy`, `atr`, ...) that Confidence, Execution,
and Market Context's own criteria already read (confirmed while preparing
Sprint 3.2's Bias data proposal). A single incoming answer for `dxy` must
therefore be able to feed `market_context.dxy` AND a future `bias.dxy`
criterion simultaneously — never just the last criterion found for that
source_field.

Reads Configuration exclusively through the four `build_*` factories
Configuration's own Application layer exposes (Sprint 3.2) — never
importing Configuration's domain or infrastructure directly
(TRADEOS_SYSTEM_ARCHITECTURE.md §3.3, Forbidden Dependencies), mirroring
the cross-module pattern established with Preferences in Sprint 1.2.

N+1 avoidance (explicitly audited this sprint): exactly three reads
regardless of engine count — scoring profiles (once, for validation),
scoring criteria (once, unfiltered, grouped by `engine_type_code`
locally), and weights for the resolved version (once, matched to each
criterion's engine via the id->engine_type_code map already built while
grouping criteria). Never one query per engine.
"""

from uuid import UUID

from app.modules.configuration.application.get_configuration_version import (
    GetConfigurationVersionUseCase,
)
from app.modules.configuration.application.list_configuration_weights import (
    ListConfigurationWeightsUseCase,
)
from app.modules.configuration.application.list_scoring_criteria import (
    ListScoringCriteriaUseCase,
)
from app.modules.configuration.application.list_scoring_profiles import (
    ListScoringProfilesUseCase,
)
from app.modules.evaluation.domain.evaluation_criterion import EvaluationCriterion
from app.modules.evaluation.domain.evaluation_engine import evaluate
from app.modules.evaluation.domain.evaluation_result import EngineInput, EvaluationResult
from app.modules.evaluation.domain.evaluation_weight import EvaluationWeight
from app.platform.errors import UnprocessableEntityError

# The five engines the generic core is instantiated for (PROJECT_AUDIT.md
# §3.2). Any criterion whose engine_type_code falls outside this set is
# ignored here rather than raising — Configuration's own EngineType
# catalog (Sprint 2.2) is the source of truth for what codes may exist;
# this Use Case only needs to know which five it must feed into evaluate().
ENGINE_TYPE_CODES = ("confidence", "quality", "execution", "market_context", "bias")


class PreviewEvaluationUseCase:
    def __init__(
        self,
        get_configuration_version_use_case: GetConfigurationVersionUseCase,
        list_scoring_criteria_use_case: ListScoringCriteriaUseCase,
        list_configuration_weights_use_case: ListConfigurationWeightsUseCase,
        list_scoring_profiles_use_case: ListScoringProfilesUseCase,
    ) -> None:
        self._get_configuration_version = get_configuration_version_use_case
        self._list_scoring_criteria = list_scoring_criteria_use_case
        self._list_configuration_weights = list_configuration_weights_use_case
        self._list_scoring_profiles = list_scoring_profiles_use_case

    async def execute(
        self,
        checklist_answers: dict[str, str | float],
        scoring_profile: str,
        configuration_version_id: UUID | None = None,
    ) -> EvaluationResult:
        profiles = await self._list_scoring_profiles.execute()
        if scoring_profile not in {profile.code for profile in profiles}:
            raise UnprocessableEntityError(
                f"'{scoring_profile}' is not a recognized scoring profile."
            )

        version = await self._get_configuration_version.execute(configuration_version_id)
        if version is None:
            raise UnprocessableEntityError(
                "No configuration version is available to evaluate against."
            )

        criteria = await self._list_scoring_criteria.execute()
        weights = await self._list_configuration_weights.execute(version.id)

        criteria_by_engine: dict[str, list[EvaluationCriterion]] = {
            code: [] for code in ENGINE_TYPE_CODES
        }
        engine_by_criterion_id: dict[str, str] = {}
        criterion_ids_by_source_field: dict[str, list[str]] = {}
        for criterion in criteria:
            engine_by_criterion_id[criterion.id] = criterion.engine_type_code
            criterion_ids_by_source_field.setdefault(criterion.source_field, []).append(
                criterion.id
            )
            if criterion.engine_type_code not in criteria_by_engine:
                continue
            criteria_by_engine[criterion.engine_type_code].append(
                EvaluationCriterion(
                    id=criterion.id,
                    name=criterion.name,
                    min_value=criterion.min_value,
                    max_value=criterion.max_value,
                    category_map=criterion.category_map,
                )
            )

        weights_by_engine: dict[str, list[EvaluationWeight]] = {
            code: [] for code in ENGINE_TYPE_CODES
        }
        for weight in weights:
            engine_type_code = engine_by_criterion_id.get(weight.criterion_id)
            if engine_type_code not in weights_by_engine:
                continue
            weights_by_engine[engine_type_code].append(
                EvaluationWeight(
                    criterion_id=weight.criterion_id,
                    profile_code=weight.profile_code,
                    weight=weight.weight,
                    is_active=weight.is_active,
                )
            )

        translated_answers: dict[str, str | float] = {
            criterion_id: value
            for source_field, value in checklist_answers.items()
            for criterion_id in criterion_ids_by_source_field.get(source_field, [])
        }

        return evaluate(
            confidence=EngineInput(
                criteria_by_engine["confidence"], weights_by_engine["confidence"]
            ),
            quality=EngineInput(criteria_by_engine["quality"], weights_by_engine["quality"]),
            execution=EngineInput(criteria_by_engine["execution"], weights_by_engine["execution"]),
            market_context=EngineInput(
                criteria_by_engine["market_context"], weights_by_engine["market_context"]
            ),
            bias=EngineInput(criteria_by_engine["bias"], weights_by_engine["bias"]),
            answers=translated_answers,
            profile_code=scoring_profile,
        )
