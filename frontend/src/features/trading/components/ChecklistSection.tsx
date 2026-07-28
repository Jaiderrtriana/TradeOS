import { useQuery } from "@tanstack/react-query";

import { ChecklistField } from "../../../components/ChecklistField";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { groupActiveCriteriaByEngine, type ChecklistAnswers } from "../../../shared/checklist";
import { listScoringCriteria, scoringReferenceKeys } from "../../../shared/scoringReferenceData";

const ENGINE_LABELS: Record<string, string> = {
  confidence: "Confidence",
  quality: "Quality",
  execution: "Execution",
  market_context: "Market Context",
  bias: "Bias",
};

const ENGINE_ORDER = ["confidence", "quality", "execution", "market_context", "bias"];

export interface ChecklistSectionProps {
  answers: ChecklistAnswers;
  onAnswerChange: (sourceField: string, value: string | number | undefined) => void;
}

/**
 * Pro mode's checklist — the same criterion-by-engine grouping and field
 * rendering `EvaluationPreviewForm` established (Sprint 3.3), reused here
 * unchanged via `src/shared/checklist.ts` + `src/components/
 * ChecklistField.tsx` (`TRADEOS_FRONTEND_BLUEPRINT.md` §8.2's
 * `ChecklistSection`).
 */
export function ChecklistSection({ answers, onAnswerChange }: ChecklistSectionProps) {
  const { data: criteria } = useQuery({
    queryKey: scoringReferenceKeys.criteria(),
    queryFn: listScoringCriteria,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const criteriaByEngine = groupActiveCriteriaByEngine(criteria ?? []);

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-sm font-semibold text-text-primary">Checklist</h3>
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
                onChange={(value) => onAnswerChange(criterion.source_field, value)}
              />
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
