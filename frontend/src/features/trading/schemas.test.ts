import { describe, expect, it } from "vitest";

import { amendTradeSchema, closeTradeSchema, tradeEntrySchema } from "./schemas";

const validTradeInput = {
  market: "EURUSD",
  direction: "long" as const,
  entry_price: 100,
  stop_loss: 95,
  scoring_profile: "day_trading",
};

describe("tradeEntrySchema", () => {
  it("accepts a valid long trade (stop below entry)", () => {
    const result = tradeEntrySchema.safeParse(validTradeInput);
    expect(result.success).toBe(true);
  });

  it("rejects a long trade whose stop is above entry (INV-TRADE-01)", () => {
    const result = tradeEntrySchema.safeParse({ ...validTradeInput, stop_loss: 105 });
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toEqual(["stop_loss"]);
    }
  });

  it("accepts a valid short trade (stop above entry)", () => {
    const result = tradeEntrySchema.safeParse({
      ...validTradeInput,
      direction: "short",
      entry_price: 100,
      stop_loss: 105,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a short trade whose stop is below entry (INV-TRADE-01)", () => {
    const result = tradeEntrySchema.safeParse({
      ...validTradeInput,
      direction: "short",
      entry_price: 100,
      stop_loss: 95,
    });
    expect(result.success).toBe(false);
  });

  it("requires market, direction, and scoring_profile", () => {
    const result = tradeEntrySchema.safeParse({ entry_price: 100, stop_loss: 95 });
    expect(result.success).toBe(false);
  });

  it("accepts optional fields when present", () => {
    const result = tradeEntrySchema.safeParse({
      ...validTradeInput,
      exit_price: 110,
      size: 1,
      leverage: "10x",
      result: "tp",
      notes: "clean breakout",
    });
    expect(result.success).toBe(true);
  });
});

describe("amendTradeSchema", () => {
  it("accepts an empty object (every field optional)", () => {
    const result = amendTradeSchema.safeParse({});
    expect(result.success).toBe(true);
  });

  it("only re-checks INV-TRADE-01 when direction, entry_price, and stop_loss are all present", () => {
    const result = amendTradeSchema.safeParse({ stop_loss: 105 });
    expect(result.success).toBe(true);
  });

  it("rejects an inconsistent full proposed state", () => {
    const result = amendTradeSchema.safeParse({
      direction: "long",
      entry_price: 100,
      stop_loss: 105,
    });
    expect(result.success).toBe(false);
  });
});

describe("closeTradeSchema", () => {
  it("requires both result and exit_price together (INV-TRADE-02, structurally)", () => {
    expect(closeTradeSchema.safeParse({ result: "tp" }).success).toBe(false);
    expect(closeTradeSchema.safeParse({ exit_price: 110 }).success).toBe(false);
    expect(closeTradeSchema.safeParse({ result: "tp", exit_price: 110 }).success).toBe(true);
  });

  it("rejects a result outside tp/sl/be", () => {
    const result = closeTradeSchema.safeParse({ result: "open", exit_price: 110 });
    expect(result.success).toBe(false);
  });
});
