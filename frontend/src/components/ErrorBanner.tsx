import type { ApiError } from "../api/errors";

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §17 — Error Experience: the user is always
 * told what happened in plain language; the raw `code` is preserved for
 * support (trace_id) but never shown as the primary message.
 */
const PRESENTATION: Record<string, string> = {
  VALIDATION_FAILED: "Some fields need correction.",
  INVARIANT_VIOLATION: "This action isn't allowed.",
  UNAUTHENTICATED: "Please sign in again.",
  FORBIDDEN: "This wasn't found.",
  NOT_FOUND: "This wasn't found.",
  CONFLICT: "This couldn't be completed right now.",
  RATE_LIMITED: "Slow down a little and try again.",
  INTERNAL_ERROR: "Something went wrong on our end.",
  NETWORK_ERROR: "Couldn't reach the server.",
  UNKNOWN_ERROR: "Something unexpected happened.",
};

export interface ErrorBannerProps {
  error: ApiError;
  onDismiss?: () => void;
}

/**
 * The single shared error-banner component — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md,
 * Sprint 0.3 deliverable. Every error, from every source, renders through
 * this one component (see ErrorContext.tsx) — never a page-specific error
 * element.
 */
export function ErrorBanner({ error, onDismiss }: ErrorBannerProps) {
  const headline = PRESENTATION[error.code] ?? PRESENTATION.UNKNOWN_ERROR;

  return (
    <div
      role="alert"
      data-testid="error-banner"
      className="flex items-start justify-between gap-4 border-b border-danger/40 bg-danger/10 px-4 py-3 text-sm text-text-primary"
    >
      <div>
        <p className="font-medium">{headline}</p>
        <p className="text-text-secondary">{error.message}</p>
        {error.traceId && (
          <p className="mt-1 font-mono text-xs text-text-muted">Reference: {error.traceId}</p>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss error"
          className="shrink-0 text-text-secondary hover:text-text-primary"
        >
          ✕
        </button>
      )}
    </div>
  );
}
