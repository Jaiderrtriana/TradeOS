import { useQuery } from "@tanstack/react-query";
import { formatInTimeZone, fromZonedTime } from "date-fns-tz";

import { apiRequest } from "../api/client";

/**
 * Sprint 4 Fase 2 (OQ-7) approved contract — the one place every other
 * module resolves/consumes timezone, so the fallback chain
 * (Preferences -> browser -> UTC) exists exactly once.
 *
 * Only for TIMESTAMPTZ-backed instants (Trade.entered_at/closed_at,
 * Journal/Playbook/Configuration created_at/updated_at/published_at).
 * Never call anything here on a pure calendar-date field
 * (Journal.period_start/period_end) — those carry no time component and
 * must never be shifted by a timezone conversion.
 */

/** `preferencesTimezone` is `Preferences.timezone` as returned by the API
 * (`null` when the user never set one explicitly). Falls back to the
 * browser's own IANA zone, and finally to UTC if `Intl` itself is
 * unavailable in this runtime. */
export function resolveTimezone(preferencesTimezone: string | null | undefined): string {
  if (preferencesTimezone) {
    return preferencesTimezone;
  }
  try {
    const browserTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (browserTimezone) {
      return browserTimezone;
    }
  } catch {
    // Intl.DateTimeFormat unavailable — fall through to the UTC default.
  }
  return "UTC";
}

/** Formats a real instant (an ISO string with an offset, as every Trade/
 * Journal/Playbook/Configuration timestamp field already is) in the
 * given IANA timezone. `timezone` is expected to already be resolved via
 * `resolveTimezone` — this function does not itself apply the fallback
 * chain, so every call site's intent stays explicit at the call site. */
export function formatInstant(
  isoInstant: string,
  timezone: string,
  formatStr = "yyyy-MM-dd HH:mm",
): string {
  return formatInTimeZone(isoInstant, timezone, formatStr);
}

/** Every IANA identifier this runtime knows about (`Intl.supportedValuesOf`,
 * native since ES2022 — no dependency, no static list to keep in sync).
 * Used only to populate the Preferences timezone selector. */
export function listIanaTimezones(): string[] {
  return Intl.supportedValuesOf("timeZone");
}

/** Constructs a tz-aware ISO datetime string from a bare
 * `<input type="date">` value (e.g. "2026-01-01"), interpreting it as
 * midnight *in the given IANA timezone* (`fromZonedTime`, DST-correct —
 * unlike `new Date("2026-01-01T00:00:00")`, which JS parses as midnight
 * in the *browser's* zone per the ECMA-262 date-time string spec, the
 * exact ambiguity this contract exists to close). This is the frontend
 * half of the Sprint 4 Fase 2 contract: the backend (`AwareDatetime`)
 * rejects anything without an explicit offset, so a date-only trade
 * entry must have one constructed here, not left for the backend to
 * guess. Returns `undefined` unchanged for an absent value (RHF's own
 * "untouched optional date input" case — see schemas.ts). */
export function dateOnlyToAwareIso(
  dateOnlyValue: string | undefined,
  timezone: string,
): string | undefined {
  if (!dateOnlyValue) {
    return dateOnlyValue;
  }
  return fromZonedTime(`${dateOnlyValue}T00:00:00`, timezone).toISOString();
}

/** Same shape as `features/settings/api.ts`'s own `PreferencesResponse`
 * — a deliberate, minimal duplication, not an import: `shared/` may only
 * depend on `shared`/`api` (ESLint `boundaries/dependencies`), never on
 * a feature's internals, matching this file's own established "own DTOs
 * per module" precedent (`evaluationPreview.ts`). Only the one field
 * this module actually needs. */
interface PreferencesTimezoneShape {
  timezone: string | null;
}

/** Shares the `["preferences"]` query key with `PreferencesPage`'s own
 * `useQuery` — React Query dedupes identical keys, so every consumer of
 * this hook adds no extra network round-trip beyond whichever component
 * asks first. Returns the *resolved* timezone (never `null`), ready to
 * pass straight to `formatInstant`. */
export function usePreferencesTimezone(): string {
  const { data } = useQuery({
    queryKey: ["preferences"],
    queryFn: () => apiRequest<PreferencesTimezoneShape>("/preferences"),
  });
  return resolveTimezone(data?.timezone);
}
