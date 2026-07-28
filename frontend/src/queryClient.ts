import { QueryClient } from "@tanstack/react-query";

/**
 * The one `QueryClient` instance for the whole app (`App.tsx`) —
 * Architecture Readiness Review (before Sprint 4.4): previously
 * `new QueryClient()` set no `defaultOptions` at all, so every query
 * silently inherited TanStack Query's own library defaults (3 retries,
 * `staleTime: 0`) instead of `TRADEOS_FRONTEND_BLUEPRINT.md` §2.7's own
 * Caching Philosophy — each feature file was re-declaring the same
 * `staleTime: 60_000` number by hand instead of there being one real
 * policy.
 *
 * Two named profiles, matching §2.7 exactly: "a short TTL for
 * Configuration/Catalog reads, always-refetch-on-navigation for
 * Trades/Statistics/Evaluation." `retry: 1` (not the default 3) app-wide
 * — a real TradeOS API failure is either a validation/business error
 * (never worth retrying) or a genuine server/network problem (worth one
 * retry, not three silent ones that delay the error the user should see,
 * consistent with `TRADEOS_FRONTEND_BLUEPRINT.md` §17's "the user is
 * always told what happened" — three silent retries before that is the
 * opposite).
 */
export const STABLE_DATA_STALE_TIME_MS = 60_000;
export const LIVE_DATA_STALE_TIME_MS = 0;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: LIVE_DATA_STALE_TIME_MS,
      retry: 1,
    },
  },
});
