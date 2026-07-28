import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ScoreRing } from "../../../components/ScoreRing";
import { Select } from "../../../components/Select";
import {
  listScoringCriteria,
  listScoringProfiles,
  scoringReferenceKeys,
  type ScoringCriterion,
} from "../../../shared/scoringReferenceData";
import { previewEvaluation } from "../api";
import { debounce } from "../debounce";
import { evaluationKeys } from "../queryKeys";
import type { ChecklistAnswers } from "../types";
import { ChecklistField } from "./ChecklistField";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";

const DEBOUNCE_MS = 500;

const ENGINE_LABELS: Record<string, string> = {
  confidence: "Confidence",
  quality: "Quality",
  execution: "Execution",
  market_context: "Market Context",
  bias: "Bias",
};

const ENGINE_ORDER = ["confidence", "quality", "execution", "market_context", "bias"];

/**
 * The live-updating Evaluation preview widget —
 * TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 3.3: "a standalone,
 * testable preview component," buildable against `POST /evaluation/preview`
 * alone. Deliberately self-contained (fetches its own reference data,
 * owns its own state) so it can be dropped into Trade Entry's Pro mode
 * later (TRADEOS_FRONTEND_BLUEPRINT.md §8.2) with no rewrite — the host
 * page supplies no props today.
 *
 * Scope this sprint (approved): five `ScoreRing`s only (score + grade;
 * Bias signed, no grade) — no per-criterion breakdown table, that is the
 * Rule Explorer's job, explicitly deferred to Phase 4
 * (TRADEOS_FRONTEND_BLUEPRINT.md §5.4; Master Plan Phase 3 notes).
 *
 * Non-blocking by design (TRADEOS_FRONTEND_BLUEPRINT.md §10, "Evaluation
 * Preview" row: "a failed preview never blocks continuing to fill the
 * form"): checklist fields are never disabled while a preview request is
 * in flight or has failed; a failure renders as a small inline message
 * here, never the app-wide `ErrorBanner` (reserved for blocking
 * mutations elsewhere, TRADEOS_FRONTEND_BLUEPRINT.md §2.8/§17).
 */
export function EvaluationPreviewForm() {
  const { data: criteria } = useQuery({
    queryKey: scoringReferenceKeys.criteria(),
    queryFn: listScoringCriteria,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const [profile, setProfile] = useState("");
  const [answers, setAnswers] = useState<ChecklistAnswers>({});
  const [debouncedProfile, setDebouncedProfile] = useState("");
  const [debouncedAnswers, setDebouncedAnswers] = useState<ChecklistAnswers>({});

  // Auto-select the first active profile once profiles load, so the
  // preview has something to show immediately (a reasonable default for
  // a demo host page; Trade Entry, when built, may override this).
  useEffect(() => {
    if (profile === "" && profiles && profiles.length > 0) {
      const firstActive = profiles.find((p) => p.is_active) ?? profiles[0];
      setProfile(firstActive.code);
    }
  }, [profile, profiles]);

  // Debounce (TRADEOS_FRONTEND_BLUEPRINT.md §6.3: "fires on change") --
  // a plain, framework-free debouncer (debounce.ts) so rapid edits to
  // multiple fields collapse into exactly one request after the user
  // pauses, rather than one request per keystroke/selection.
  const debouncedUpdateRef = useRef(
    debounce((nextAnswers: ChecklistAnswers, nextProfile: string) => {
      setDebouncedAnswers(nextAnswers);
      setDebouncedProfile(nextProfile);
    }, DEBOUNCE_MS),
  );

  useEffect(() => {
    debouncedUpdateRef.current(answers, profile);
  }, [answers, profile]);

  useEffect(() => {
    const debouncedUpdate = debouncedUpdateRef.current;
    return () => debouncedUpdate.cancel();
  }, []);

  const {
    data: snapshot,
    error,
    isFetching,
  } = useQuery({
    queryKey: evaluationKeys.preview(debouncedProfile, debouncedAnswers),
    queryFn: () =>
      previewEvaluation({ checklist_answers: debouncedAnswers, scoring_profile: debouncedProfile }),
    enabled: debouncedProfile !== "",
    // Keeps the last good snapshot visible while a newer debounced
    // request is in flight, instead of flashing to empty -- also the
    // mechanism that makes an out-of-order/slow response harmless: only
    // the result matching the *current* queryKey is ever shown.
    placeholderData: keepPreviousData,
    // No automatic retry: TRADEOS_FRONTEND_BLUEPRINT.md §10's Evaluation
    // Preview row is explicit that a failure renders "inline" -- silently
    // retrying (React Query's 3-attempt default) could hide a real
    // failure from the user for several seconds. Recovery instead happens
    // the way every other field update already works: the user's next
    // edit fires a new debounced query.
    retry: false,
  });

  const criteriaByEngine = groupActiveCriteriaByEngine(criteria ?? []);

  function handleAnswerChange(sourceField: string, value: string | number | undefined) {
    setAnswers((previous) => upsertChecklistAnswer(previous, sourceField, value));
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="mb-1 text-sm text-text-secondary">Scoring Profile</p>
        <Select
          value={profile}
          onValueChange={setProfile}
          options={(profiles ?? []).map((p) => ({ value: p.code, label: p.display_name }))}
          aria-label="Scoring Profile"
        />
      </div>

      <div className="flex flex-col gap-4">
        {ENGINE_ORDER.filter((engine) => criteriaByEngine[engine]?.length).map((engine) => (
          <details key={engine} className="rounded border border-border">
            <summary className="cursor-pointer px-4 py-2 text-sm font-medium text-text-primary">
              {ENGINE_LABELS[engine] ?? engine}
            </summary>
            <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2">
              {criteriaByEngine[engine].map((criterion) => (
                <ChecklistField
                  key={criterion.id}
                  criterion={criterion}
                  value={answers[criterion.source_field]}
                  onChange={(value) => handleAnswerChange(criterion.source_field, value)}
                />
              ))}
            </div>
          </details>
        ))}
      </div>

      <div>
        <div className="mb-2 flex items-center gap-3">
          <h3 className="text-sm font-semibold text-text-primary">Preview</h3>
          {isFetching && <span className="text-xs text-text-muted">Updating…</span>}
        </div>

        {error && (
          <p role="alert" className="mb-3 text-sm text-danger">
            Couldn&apos;t compute a preview right now. Your answers are unaffected — keep filling
            the checklist; it will retry automatically.
          </p>
        )}

        {snapshot ? (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <ScoreRing
              label="Confidence"
              score={snapshot.confidence.score}
              grade={snapshot.confidence.grade}
            />
            <ScoreRing
              label="Quality"
              score={snapshot.quality.score}
              grade={snapshot.quality.grade}
            />
            <ScoreRing
              label="Execution"
              score={snapshot.execution.score}
              grade={snapshot.execution.grade}
            />
            <ScoreRing
              label="Market Context"
              score={snapshot.market_context.score}
              grade={snapshot.market_context.grade}
            />
            <ScoreRing label="Bias" score={snapshot.bias.score} />
          </div>
        ) : (
          <p className="text-sm text-text-secondary">
            {profile === "" ? "Loading scoring profiles…" : "Answer the checklist to see scores."}
          </p>
        )}
      </div>
    </div>
  );
}

/** Exported for unit testing (evaluationLogic.test.ts) independent of rendering. */
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
 * Pure `checklist_answers` construction — a field with `value === undefined`
 * (the user cleared it) is *removed* from the map entirely, never sent as
 * `null`/`""`, matching TRADEOS_API_SPECIFICATION.md line 190: "Omitted
 * fields simply mean those criteria don't contribute." Exported for unit
 * testing independent of rendering.
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
