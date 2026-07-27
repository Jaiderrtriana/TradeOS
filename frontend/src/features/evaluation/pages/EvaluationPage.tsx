import { EvaluationPreviewForm } from "../components/EvaluationPreviewForm";

/**
 * Demo host for Sprint 3.3's deliverable — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md:
 * "a standalone, testable preview component," shown here at `/evaluation`
 * only because Trade Entry (Phase 4) doesn't exist yet to embed it in
 * (TRADEOS_FRONTEND_BLUEPRINT.md §8.2's `NewTradeModal` is where it
 * belongs long-term). This page owns no preview logic itself — it is
 * purely a route that renders `EvaluationPreviewForm`, which is fully
 * self-contained and takes no props, so embedding it elsewhere later is
 * a one-line change, not a rewrite.
 */
export function EvaluationPage() {
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-text-primary">Evaluation Preview</h1>
      <p className="mt-1 text-sm text-text-secondary">
        Answer the checklist below to see a live, non-blocking preview of all five Evaluation Engine
        scores.
      </p>
      <div className="mt-6">
        <EvaluationPreviewForm />
      </div>
    </div>
  );
}
