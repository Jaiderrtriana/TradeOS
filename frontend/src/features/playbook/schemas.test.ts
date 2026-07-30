import { describe, expect, it } from "vitest";

import { addPlaybookSetupAttachmentSchema, updatePlaybookSetupSchema } from "./schemas";

describe("updatePlaybookSetupSchema", () => {
  it("accepts all four fields, including empty strings", () => {
    const result = updatePlaybookSetupSchema.safeParse({
      entry_criteria: "Break of structure",
      exit_criteria: "",
      ideal_conditions: "High volume session",
      risk_rules: "Max 1% risk",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a missing field rather than silently defaulting it", () => {
    const { entry_criteria, ...rest } = {
      entry_criteria: "x",
      exit_criteria: "x",
      ideal_conditions: "x",
      risk_rules: "x",
    };
    void entry_criteria;
    expect(updatePlaybookSetupSchema.safeParse(rest).success).toBe(false);
  });
});

describe("addPlaybookSetupAttachmentSchema", () => {
  it("accepts a file reference with an optional caption", () => {
    const result = addPlaybookSetupAttachmentSchema.safeParse({
      file_reference: "https://example.com/chart.png",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an empty file reference", () => {
    expect(
      addPlaybookSetupAttachmentSchema.safeParse({ file_reference: "" }).success,
    ).toBe(false);
  });
});
