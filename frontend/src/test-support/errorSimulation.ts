import { parseApiError, type ApiError } from "../api/errors";

/**
 * Dev/test-only hook so Playwright can prove the shared error path end to
 * end (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 0.3 Exit Criteria:
 * "a simulated API error renders through the one shared error path, not a
 * page-specific handler") without any real endpoint existing yet — no
 * business feature triggers this, only an E2E test does.
 *
 * Guarded by import.meta.env.DEV so Vite tree-shakes it out of the
 * production build entirely.
 */
declare global {
  interface Window {
    __tradeosSimulateApiError?: () => void;
  }
}

export function installErrorSimulationHook(reportError: (error: ApiError) => void): void {
  if (!import.meta.env.DEV) {
    return;
  }

  window.__tradeosSimulateApiError = () => {
    const simulatedEnvelope = {
      error: {
        code: "INTERNAL_ERROR",
        message: "Simulated internal error for Sprint 0.3 verification.",
        details: [],
        trace_id: "test-trace-id-0001",
        timestamp: new Date().toISOString(),
      },
    };
    reportError(parseApiError(500, simulatedEnvelope));
  };
}
