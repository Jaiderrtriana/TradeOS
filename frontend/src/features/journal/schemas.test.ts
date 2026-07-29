import { describe, expect, it } from "vitest";

import { journalContentSchema, periodJournalEntrySchema } from "./schemas";

describe("journalContentSchema", () => {
  it("accepts non-empty content", () => {
    expect(journalContentSchema.safeParse({ content: "Waited for confirmation." }).success).toBe(
      true,
    );
  });

  it("rejects empty content", () => {
    expect(journalContentSchema.safeParse({ content: "" }).success).toBe(false);
  });
});

describe("periodJournalEntrySchema", () => {
  const valid = { content: "Weekly review.", period_start: "2026-07-20", period_end: "2026-07-26" };

  it("accepts a complete period-scoped entry", () => {
    expect(periodJournalEntrySchema.safeParse(valid).success).toBe(true);
  });

  it("rejects a missing period_start", () => {
    const { period_start, ...rest } = valid;
    void period_start;
    expect(periodJournalEntrySchema.safeParse(rest).success).toBe(false);
  });

  it("rejects a missing period_end", () => {
    const { period_end, ...rest } = valid;
    void period_end;
    expect(periodJournalEntrySchema.safeParse(rest).success).toBe(false);
  });

  it("rejects empty content", () => {
    expect(periodJournalEntrySchema.safeParse({ ...valid, content: "" }).success).toBe(false);
  });

  it("does not enforce period_end >= period_start (no such rule in the backend)", () => {
    const result = periodJournalEntrySchema.safeParse({
      ...valid,
      period_start: "2026-07-26",
      period_end: "2026-07-20",
    });
    expect(result.success).toBe(true);
  });
});
