import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { ScoreRing } from "../../../components/ScoreRing";
import type { ChecklistAnswers } from "../../../shared/checklist";
import { debounce } from "../../../shared/debounce";
import { evaluationPreviewKeys, previewEvaluation } from "../../../shared/evaluationPreview";

const DEBOUNCE_MS = 500;

export interface TradeEntryScorePreviewProps {
  scoringProfile: string;
  checklistAnswers: ChecklistAnswers;
}

/**
 * Pro mode's live score preview — `TRADEOS_FRONTEND_BLUEPRINT.md` §6.3:
 * "checklist_answers → POST /evaluation/preview fires on change → score
 * preview updates in place, non-blocking." The same debounced-preview
 * pattern `EvaluationPreviewForm` established (Sprint 3.3), reused here
 * via `src/shared/evaluationPreview.ts` + `src/shared/debounce.ts` — this
 * call is advisory only and never itself creates or reserves a Trade
 * (`TRADEOS_API_SPECIFICATION.md` §6.5).
 */
export function TradeEntryScorePreview({
  scoringProfile,
  checklistAnswers,
}: TradeEntryScorePreviewProps) {
  const [debouncedProfile, setDebouncedProfile] = useState("");
  const [debouncedAnswers, setDebouncedAnswers] = useState<ChecklistAnswers>({});

  const debouncedUpdateRef = useRef(
    debounce((nextAnswers: ChecklistAnswers, nextProfile: string) => {
      setDebouncedAnswers(nextAnswers);
      setDebouncedProfile(nextProfile);
    }, DEBOUNCE_MS),
  );

  useEffect(() => {
    debouncedUpdateRef.current(checklistAnswers, scoringProfile);
  }, [checklistAnswers, scoringProfile]);

  useEffect(() => {
    const debouncedUpdate = debouncedUpdateRef.current;
    return () => debouncedUpdate.cancel();
  }, []);

  const {
    data: snapshot,
    error,
    isFetching,
  } = useQuery({
    queryKey: evaluationPreviewKeys.preview(debouncedProfile, debouncedAnswers),
    queryFn: () =>
      previewEvaluation({ checklist_answers: debouncedAnswers, scoring_profile: debouncedProfile }),
    enabled: debouncedProfile !== "",
    placeholderData: keepPreviousData,
    retry: false,
  });

  return (
    <div>
      <div className="mb-2 flex items-center gap-3">
        <h3 className="text-sm font-semibold text-text-primary">Preview</h3>
        {isFetching && <span className="text-xs text-text-muted">Updating…</span>}
      </div>

      {error && (
        <p role="alert" className="mb-3 text-sm text-danger">
          Couldn&apos;t compute a preview right now. Your answers are unaffected — keep filling the
          checklist; it will retry automatically.
        </p>
      )}

      {snapshot ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <ScoreRing
            label="Confidence"
            score={snapshot.confidence.score}
            grade={snapshot.confidence.grade}
          />
          <ScoreRing label="Quality" score={snapshot.quality.score} grade={snapshot.quality.grade} />
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
          {scoringProfile === "" ? "Select a scoring profile…" : "Answer the checklist to see scores."}
        </p>
      )}
    </div>
  );
}
