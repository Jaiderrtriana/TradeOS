import type { ScoringCriterion } from "./scoringReferenceData";

/**
 * Checklist-answer shape and pure logic — moved to `src/shared/` from
 * `features/evaluation/` (Sprint 4.4): the raw `{criterion_source_field:
 * value}` map (`TRADEOS_API_SPECIFICATION.md` §6.4) is submitted by both
 * `POST /evaluation/preview` (Evaluation's own preview) and `POST /trades`
 * (Trading's Pro mode, via the same live-preview pattern) — genuinely
 * identical logic needed by two features, same reasoning as
 * `scoringReferenceData.ts`. `groupActiveCriteriaByEngine` and
 * `upsertChecklistAnswer` were originally exported from
 * `EvaluationPreviewForm.tsx` itself for unit testing; both are pure and
 * carry no Evaluation-specific behavior, so they move here unchanged.
 */
export type ChecklistAnswers = Record<string, string | number>;

export function groupActiveCriteriaByEngine(
  criteria: ScoringCriterion[],
): Record<string, ScoringCriterion[]> {
  const grouped: Record<string, ScoringCriterion[]> = {};
  for (const criterion of criteria) {
    if (!criterion.is_active) {
      continue;
    }
    (grouped[criterion.engine_type_code] ??= []).push(criterion);
  }
  return grouped;
}

/**
 * A field with `value === undefined` (the user cleared it) is *removed*
 * from the map entirely, never sent as `null`/`""`, matching
 * `TRADEOS_API_SPECIFICATION.md`: "Omitted fields simply mean those
 * criteria don't contribute."
 */
export function upsertChecklistAnswer(
  answers: ChecklistAnswers,
  sourceField: string,
  value: string | number | undefined,
): ChecklistAnswers {
  const next = { ...answers };
  if (value === undefined) {
    delete next[sourceField];
  } else {
    next[sourceField] = value;
  }
  return next;
}
