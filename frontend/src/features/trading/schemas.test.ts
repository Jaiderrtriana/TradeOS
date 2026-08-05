import { describe, expect, it } from "vitest";

import { amendTradeSchema, buildOpenTradeSchema, closeTradeSchema, tradeEntrySchema } from "./schemas";

const validTradeInput = {
  market: "EURUSD",
  direction: "long" as const,
  status: "open" as const,
  entry_price: 100,
  stop_loss: 95,
  entered_at: "2026-01-01T00:00:00Z",
  scoring_profile: "day_trading",
};

describe("tradeEntrySchema", () => {
  it("accepts a valid open long trade (stop below entry)", () => {
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

  it("requires market, direction, and status", () => {
    const result = tradeEntrySchema.safeParse({ entry_price: 100, stop_loss: 95 });
    expect(result.success).toBe(false);
  });

  it("requires scoring_profile, entry_price, and entered_at once status != planned", () => {
    const result = tradeEntrySchema.safeParse({ market: "EURUSD", direction: "long", status: "open" });
    expect(result.success).toBe(false);
    if (!result.success) {
      const paths = result.error.issues.map((issue) => issue.path[0]);
      expect(paths).toContain("scoring_profile");
      expect(paths).toContain("entry_price");
      expect(paths).toContain("entered_at");
    }
  });

  it("accepts a bare planned trade with no entry facts or scoring_profile", () => {
    const result = tradeEntrySchema.safeParse({ market: "EURUSD", direction: "long", status: "planned" });
    expect(result.success).toBe(true);
  });

  it("rejects a planned trade that already carries an entry_price", () => {
    const result = tradeEntrySchema.safeParse({
      market: "EURUSD",
      direction: "long",
      status: "planned",
      entry_price: 100,
    });
    expect(result.success).toBe(false);
  });

  it("requires exit_price, result, closed_at, and realized_pnl when status = closed", () => {
    const result = tradeEntrySchema.safeParse(validTradeInput /* status: open, no close facts */);
    expect(result.success).toBe(true); // valid as Open

    const closedAttempt = tradeEntrySchema.safeParse({ ...validTradeInput, status: "closed" });
    expect(closedAttempt.success).toBe(false);
    if (!closedAttempt.success) {
      const paths = closedAttempt.error.issues.map((issue) => issue.path[0]);
      expect(paths).toContain("exit_price");
      expect(paths).toContain("result");
      expect(paths).toContain("closed_at");
      expect(paths).toContain("realized_pnl");
    }
  });

  it("accepts a fully specified closed trade", () => {
    const result = tradeEntrySchema.safeParse({
      ...validTradeInput,
      status: "closed",
      exit_price: 110,
      result: "tp",
      closed_at: "2026-01-02T00:00:00Z",
      realized_pnl: 80,
    });
    expect(result.success).toBe(true);
  });

  it("accepts optional fields when present", () => {
    const result = tradeEntrySchema.safeParse({
      ...validTradeInput,
      status: "closed",
      exit_price: 110,
      size: 1,
      leverage: "10x",
      result: "tp",
      closed_at: "2026-01-02T00:00:00Z",
      realized_pnl: 80,
      take_profit: 115,
      margin_used: 50,
      notes: "clean breakout",
    });
    expect(result.success).toBe(true);
  });
});

describe("buildOpenTradeSchema", () => {
  const openTradeSchema = buildOpenTradeSchema("long");

  it("requires entry_price, entered_at, and scoring_profile", () => {
    expect(openTradeSchema.safeParse({}).success).toBe(false);
    expect(
      openTradeSchema.safeParse({
        entry_price: 100,
        entered_at: "2026-01-01T00:00:00Z",
        scoring_profile: "day_trading",
      }).success,
    ).toBe(true);
  });

  it("re-validates INV-TRADE-01 against the fixed direction it was built for", () => {
    const result = openTradeSchema.safeParse({
      entry_price: 100,
      entered_at: "2026-01-01T00:00:00Z",
      scoring_profile: "day_trading",
      stop_loss: 105, // long, stop above entry -- invalid
    });
    expect(result.success).toBe(false);
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

  it("accepts take_profit and margin_used", () => {
    const result = amendTradeSchema.safeParse({ take_profit: 120, margin_used: 50 });
    expect(result.success).toBe(true);
  });
});

describe("closeTradeSchema", () => {
  const base = { realized_pnl: 80, closed_at: "2026-01-02T00:00:00Z" };

  it("requires result and exit_price together (INV-TRADE-02, structurally)", () => {
    expect(closeTradeSchema.safeParse({ ...base, result: "tp" }).success).toBe(false);
    expect(closeTradeSchema.safeParse({ ...base, exit_price: 110 }).success).toBe(false);
    expect(closeTradeSchema.safeParse({ ...base, result: "tp", exit_price: 110 }).success).toBe(true);
  });

  it("requires realized_pnl and closed_at", () => {
    const result = closeTradeSchema.safeParse({ result: "tp", exit_price: 110 });
    expect(result.success).toBe(false);
  });

  it("rejects a result outside tp/sl/be", () => {
    const result = closeTradeSchema.safeParse({ ...base, result: "open", exit_price: 110 });
    expect(result.success).toBe(false);
  });
});
