import { Badge, type BadgeTone } from "./Badge";

/**
 * Shared ScoreRing / ScoreBar — TRADEOS_FRONTEND_BLUEPRINT.md §7:
 * "Visualize one Evaluation Engine's score/grade... Reuse: Trade Detail,
 * Rule Explorer." First built here (Sprint 3.3, Evaluation Preview); a
 * shared component per §2.4/§7 so Trade Detail and the Rule Explorer
 * (Phase 4) reuse it unchanged rather than re-implementing the same
 * visualization.
 *
 * `grade` is `null` for every unsigned engine's *possible* input shape,
 * but the caller must omit it entirely (not pass `null`) for Bias — Bias
 * is signed and structurally never has a grade
 * (TRADEOS_DATABASE_DESIGN.md §6.12, no `bias_grade` column). That
 * distinction is carried in the type: `grade` is only ever present when
 * the engine is one of the four graded ones.
 *
 * Colors reuse the existing, small token set only (TRADEOS_FRONTEND_BLUEPRINT.md
 * §14: "a component that invents its own... color unit is a defect") —
 * no new CSS variables introduced this sprint.
 */
const GRADE_TONE: Record<string, BadgeTone> = {
  "A+": "accent",
  A: "accent",
  B: "neutral",
  C: "neutral",
  D: "muted",
};

export interface ScoreRingProps {
  label: string;
  score: number;
  /** Omit entirely for Bias (signed, never graded) — see module docstring. */
  grade?: string | null;
}

export function ScoreRing({ label, score, grade }: ScoreRingProps) {
  const isSigned = grade === undefined;
  const signedTone: BadgeTone = score > 0 ? "accent" : score < 0 ? "muted" : "neutral";

  return (
    <div
      className="flex flex-col items-center gap-2 rounded border border-border bg-bg-surface p-4"
      data-testid={`score-ring-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <p className="text-sm text-text-secondary">{label}</p>
      <p className="font-mono text-2xl font-semibold text-text-primary">
        {isSigned && score > 0 ? "+" : ""}
        {score}
      </p>
      {isSigned ? (
        <Badge label="signed" tone={signedTone} />
      ) : (
        <Badge label={grade ?? "—"} tone={grade ? (GRADE_TONE[grade] ?? "neutral") : "muted"} />
      )}
    </div>
  );
}
