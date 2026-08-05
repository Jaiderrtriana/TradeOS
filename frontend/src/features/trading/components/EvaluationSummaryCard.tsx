import { Link } from "react-router-dom";

import { ScoreRing } from "../../../components/ScoreRing";
import type { EvaluationSnapshot } from "../types";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.3/§8.3/§12: five `ScoreRing`s plus
 * a "View full breakdown" link into the Rule Explorer (§5.4) — the
 * per-criterion breakdown table itself is explicitly that page's job,
 * not this card's.
 *
 * v2.0 (Domain Invariant DI-13): `evaluation` is `null` for a `Planned`
 * Trade — no Evaluation exists yet, since Evaluation only runs once the
 * Trade transitions to `Open` (`POST /trades/{id}/open`) or is registered
 * directly as `Open`/`Closed`.
 */
export function EvaluationSummaryCard({
  tradeId,
  evaluation,
}: {
  tradeId: string;
  evaluation: EvaluationSnapshot | null;
}) {
  if (evaluation === null) {
    return (
      <div className="rounded border border-border bg-bg-surface p-4">
        <h2 className="text-base font-semibold text-text-primary">Evaluation</h2>
        <p className="mt-2 text-sm text-text-secondary">
          This trade is still Planned — it has no Evaluation yet. Opening it will run the first
          Evaluation.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">Evaluation</h2>
        <Link to={`/trades/${tradeId}/evaluation`} className="text-sm text-accent">
          View full breakdown
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-5">
        <ScoreRing
          label="Confidence"
          score={evaluation.confidence.score ?? 0}
          grade={evaluation.confidence.grade}
        />
        <ScoreRing
          label="Quality"
          score={evaluation.quality.score ?? 0}
          grade={evaluation.quality.grade}
        />
        <ScoreRing
          label="Execution"
          score={evaluation.execution.score ?? 0}
          grade={evaluation.execution.grade}
        />
        <ScoreRing
          label="Market Context"
          score={evaluation.market_context.score ?? 0}
          grade={evaluation.market_context.grade}
        />
        <ScoreRing label="Bias" score={evaluation.bias.score ?? 0} />
      </div>
    </div>
  );
}
