import { describe, expect, it } from "vitest";

import { groupActiveCriteriaByEngine, upsertChecklistAnswer } from "./checklist";
import type { ScoringCriterion } from "./scoringReferenceData";

function criterion(overrides: Partial<ScoringCriterion>): ScoringCriterion {
  return {
    id: "x.y",
    engine_type_code: "confidence",
    category: null,
    name: "X",
    description: "",
    source_field: "y",
    min_value: 0,
    max_value: 100,
    category_map: null,
    is_active: true,
    ...overrides,
  };
}

describe("groupActiveCriteriaByEngine", () => {
  it("groups criteria by engine_type_code", () => {
    const criteria = [
      criterion({ id: "confidence.a", engine_type_code: "confidence" }),
      criterion({ id: "bias.a", engine_type_code: "bias" }),
      criterion({ id: "confidence.b", engine_type_code: "confidence" }),
    ];

    const grouped = groupActiveCriteriaByEngine(criteria);

    expect(grouped.confidence?.map((c) => c.id)).toEqual(["confidence.a", "confidence.b"]);
    expect(grouped.bias?.map((c) => c.id)).toEqual(["bias.a"]);
  });

  it("excludes inactive criteria (never presented as answerable)", () => {
    const criteria = [
      criterion({ id: "confidence.active", is_active: true }),
      criterion({ id: "confidence.inactive", is_active: false }),
    ];

    const grouped = groupActiveCriteriaByEngine(criteria);

    expect(grouped.confidence?.map((c) => c.id)).toEqual(["confidence.active"]);
  });
});

describe("upsertChecklistAnswer", () => {
  it("adds a new answer", () => {
    const result = upsertChecklistAnswer({}, "dxy", "Strong Bullish");
    expect(result).toEqual({ dxy: "Strong Bullish" });
  });

  it("overwrites an existing answer for the same field", () => {
    const result = upsertChecklistAnswer({ dxy: "Neutral" }, "dxy", "Bearish");
    expect(result).toEqual({ dxy: "Bearish" });
  });

  it("removes the field entirely when value is undefined (cleared, not sent as null)", () => {
    const result = upsertChecklistAnswer({ dxy: "Bearish", spy: "Range" }, "dxy", undefined);
    expect(result).toEqual({ spy: "Range" });
    expect("dxy" in result).toBe(false);
  });

  it("never mutates the input map", () => {
    const original = { dxy: "Neutral" };
    upsertChecklistAnswer(original, "dxy", "Bullish");
    expect(original).toEqual({ dxy: "Neutral" });
  });
});
