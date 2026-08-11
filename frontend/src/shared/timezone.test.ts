import { afterEach, describe, expect, it, vi } from "vitest";

import { dateOnlyToAwareIso, formatInstant, listIanaTimezones, resolveTimezone } from "./timezone";

describe("resolveTimezone", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the explicit Preferences.timezone when set", () => {
    expect(resolveTimezone("America/Bogota")).toBe("America/Bogota");
  });

  it("falls back to the browser-detected timezone when null (never set)", () => {
    vi.spyOn(Intl, "DateTimeFormat").mockImplementation(
      () => ({ resolvedOptions: () => ({ timeZone: "Europe/Madrid" }) }) as Intl.DateTimeFormat,
    );
    expect(resolveTimezone(null)).toBe("Europe/Madrid");
  });

  it("falls back to the browser-detected timezone when undefined", () => {
    vi.spyOn(Intl, "DateTimeFormat").mockImplementation(
      () => ({ resolvedOptions: () => ({ timeZone: "Asia/Tokyo" }) }) as Intl.DateTimeFormat,
    );
    expect(resolveTimezone(undefined)).toBe("Asia/Tokyo");
  });

  it("falls back to UTC if Intl.DateTimeFormat itself is unavailable", () => {
    vi.spyOn(Intl, "DateTimeFormat").mockImplementation(() => {
      throw new Error("Intl unavailable in this runtime");
    });
    expect(resolveTimezone(null)).toBe("UTC");
  });
});

describe("dateOnlyToAwareIso — DST-correct conversion (Sprint 4 Fase 2, OQ-7 contract)", () => {
  it("anchors a date-only value to midnight in a fixed-offset zone (no DST)", () => {
    // America/Bogota is UTC-5 year-round -- midnight there is 05:00 UTC.
    expect(dateOnlyToAwareIso("2026-01-01", "America/Bogota")).toBe("2026-01-01T05:00:00.000Z");
  });

  it("applies the DST-shifted offset for a summer date in a DST-observing zone", () => {
    // America/New_York is UTC-4 (EDT) in June -- midnight there is 04:00 UTC.
    expect(dateOnlyToAwareIso("2026-06-01", "America/New_York")).toBe("2026-06-01T04:00:00.000Z");
  });

  it("applies the non-DST offset for a winter date in the same zone", () => {
    // America/New_York is UTC-5 (EST) in January -- midnight there is 05:00 UTC.
    expect(dateOnlyToAwareIso("2026-01-01", "America/New_York")).toBe("2026-01-01T05:00:00.000Z");
  });

  it("leaves UTC unchanged", () => {
    expect(dateOnlyToAwareIso("2026-01-01", "UTC")).toBe("2026-01-01T00:00:00.000Z");
  });

  it("passes an absent value through unchanged (RHF's untouched-optional-date case)", () => {
    expect(dateOnlyToAwareIso(undefined, "America/Bogota")).toBeUndefined();
    expect(dateOnlyToAwareIso("", "America/Bogota")).toBe("");
  });
});

describe("formatInstant", () => {
  it("formats a real UTC instant in the given IANA timezone", () => {
    // 2026-01-01T05:00:00Z is 2026-01-01 00:00 in Bogota (UTC-5).
    expect(formatInstant("2026-01-01T05:00:00Z", "America/Bogota")).toBe("2026-01-01 00:00");
  });

  it("never shifts a pure calendar date (Journal.period_start/period_end) — only ever called on real instants", () => {
    // No production call site passes a date-only string (e.g.
    // "2026-01-01") to this function -- period_start/period_end are
    // rendered as the raw API string everywhere (JournalEntryDetailPage,
    // JournalListPage), never through formatInstant. This test documents
    // that boundary at the unit level: even if a bare date string were
    // passed by mistake, it is treated as UTC midnight (the ECMA-262
    // date-only parsing rule), not reinterpreted as a business date --
    // proof that this function is only ever safe to use on genuine
    // TIMESTAMPTZ-backed instants, never on a Date field.
    expect(formatInstant("2026-01-01", "UTC")).toBe("2026-01-01 00:00");
  });
});

describe("listIanaTimezones", () => {
  it("returns real IANA identifiers, not fixed offsets", () => {
    const zones = listIanaTimezones();
    expect(zones).toContain("America/Bogota");
    expect(zones).toContain("Europe/Madrid");
    expect(zones.some((zone) => zone.startsWith("UTC-") || zone.startsWith("GMT-"))).toBe(false);
  });
});
