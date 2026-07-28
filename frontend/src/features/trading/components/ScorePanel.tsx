import { DataTable } from "../../../components/DataTable";
import { ScoreRing } from "../../../components/ScoreRing";
import type { BiasEngineResult, CriterionBreakdownRow, GradedEngineResult } from "../types";

export interface ScorePanelProps {
  label: string;
  result: GradedEngineResult | BiasEngineResult;
}

function hasGrade(
  result: GradedEngineResult | BiasEngineResult,
): result is GradedEngineResult {
  return "grade" in result;
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.4/§8.4's `ScorePanel`: a `ScoreRing`
 * plus its criterion-level breakdown table (criterion, raw value,
 * normalized value, weight, contribution — exactly
 * `TRADEOS_API_SPECIFICATION.md` §6.5's shape). One per Engine, reused
 * for both the current snapshot and any selected historical one.
 */
export function ScorePanel({ label, result }: ScorePanelProps) {
  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <ScoreRing
        label={label}
        score={result.score ?? 0}
        grade={hasGrade(result) ? result.grade : undefined}
      />
      <div className="mt-4">
        {result.breakdown.length === 0 ? (
          <p className="text-sm text-text-secondary">No criteria contributed to this score.</p>
        ) : (
          <DataTable<CriterionBreakdownRow>
            columns={[
              { key: "criterion_name", header: "Criterion", render: (r) => r.criterion_name },
              { key: "raw_value", header: "Raw Value", render: (r) => r.raw_value },
              {
                key: "normalized_value",
                header: "Normalized",
                render: (r) => r.normalized_value.toFixed(2),
              },
              { key: "weight", header: "Weight", render: (r) => r.weight.toFixed(2) },
              { key: "contribution", header: "Contribution", render: (r) => r.contribution.toFixed(2) },
            ]}
            rows={result.breakdown}
            getRowKey={(r) => r.criterion_id}
          />
        )}
      </div>
    </div>
  );
}
