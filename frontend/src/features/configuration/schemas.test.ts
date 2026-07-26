import { describe, expect, it } from "vitest";

import {
  createCatalogEntrySchema,
  createDraftVersionSchema,
  renameCatalogEntrySchema,
  weightFormSchema,
} from "./schemas";

describe("createDraftVersionSchema", () => {
  it("accepts a non-empty label within 40 characters", () => {
    expect(createDraftVersionSchema.safeParse({ version_label: "v1.1" }).success).toBe(true);
  });

  it("rejects an empty label", () => {
    expect(createDraftVersionSchema.safeParse({ version_label: "" }).success).toBe(false);
  });

  it("rejects a label longer than 40 characters (matches Field(max_length=40))", () => {
    const tooLong = "v".repeat(41);
    expect(createDraftVersionSchema.safeParse({ version_label: tooLong }).success).toBe(false);
  });
});

describe("weightFormSchema", () => {
  it("accepts a valid weight and coerces the raw string input to a number", () => {
    const result = weightFormSchema.safeParse({
      criterion_id: "confidence.htf_alignment",
      profile_code: "day_trading",
      weight: "0.25",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.weight).toBe(0.25);
    }
  });

  it("rejects a negative weight (matches Field(ge=0))", () => {
    const result = weightFormSchema.safeParse({
      criterion_id: "confidence.htf_alignment",
      profile_code: "day_trading",
      weight: "-1",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an empty criterion selection", () => {
    const result = weightFormSchema.safeParse({
      criterion_id: "",
      profile_code: "day_trading",
      weight: "0.5",
    });
    expect(result.success).toBe(false);
  });
});

describe("createCatalogEntrySchema", () => {
  it("accepts a valid kind and name", () => {
    const result = createCatalogEntrySchema.safeParse({ kind: "setup", name: "Pullback" });
    expect(result.success).toBe(true);
  });

  it("rejects a kind outside the five confirmed kinds", () => {
    const result = createCatalogEntrySchema.safeParse({ kind: "not_a_kind", name: "X" });
    expect(result.success).toBe(false);
  });

  it("rejects a name longer than 120 characters (matches Field(max_length=120))", () => {
    const tooLong = "x".repeat(121);
    const result = createCatalogEntrySchema.safeParse({ kind: "setup", name: tooLong });
    expect(result.success).toBe(false);
  });
});

describe("renameCatalogEntrySchema", () => {
  it("accepts a non-empty name", () => {
    expect(renameCatalogEntrySchema.safeParse({ name: "Renamed" }).success).toBe(true);
  });

  it("rejects an empty name", () => {
    expect(renameCatalogEntrySchema.safeParse({ name: "" }).success).toBe(false);
  });
});
