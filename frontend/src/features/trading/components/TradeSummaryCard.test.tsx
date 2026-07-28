import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { TradeDetail } from "../types";
import { TradeSummaryCard } from "./TradeSummaryCard";

const EMPTY_ENGINE = { score: null, grade: null, breakdown: [] };
const EMPTY_BIAS = { score: null, breakdown: [] };

function buildTrade(overrides: Partial<TradeDetail> = {}): TradeDetail {
  return {
    id: "trade-1",
    market: "EURUSD",
    direction: "long",
    entry_price: 100,
    stop_loss: 95,
    exit_price: null,
    size: 1,
    leverage: "",
    result: "open",
    realized_pnl: 0,
    mfe_price: null,
    mae_price: null,
    notes: "",
    strategy_id: null,
    setup_id: null,
    session_id: null,
    entry_trigger_id: null,
    entered_at: "2026-07-01T00:00:00Z",
    closed_at: null,
    created_at: "2026-07-01T00:00:00Z",
    updated_at: "2026-07-01T00:00:00Z",
    r_multiple: null,
    mfe_r: null,
    mae_r: null,
    captured_pct: null,
    potential_left_r: null,
    checklist_answers: {},
    evaluation: {
      confidence: EMPTY_ENGINE,
      quality: EMPTY_ENGINE,
      execution: EMPTY_ENGINE,
      market_context: EMPTY_ENGINE,
      bias: EMPTY_BIAS,
    },
    ...overrides,
  };
}

describe("TradeSummaryCard", () => {
  it("renders the market as a heading and the direction/result badges", () => {
    render(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.getByRole("heading", { name: "EURUSD" })).toBeInTheDocument();
    expect(screen.getByText("Long")).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
  });

  it("shows an em dash for every not-yet-computed field on an open trade", () => {
    render(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.getByText("Exit Price").nextSibling).toHaveTextContent("—");
    expect(screen.getByText("R-Multiple").nextSibling).toHaveTextContent("—");
  });

  it("renders computed values once the trade is closed", () => {
    render(
      <TradeSummaryCard
        trade={buildTrade({
          result: "tp",
          exit_price: 110,
          r_multiple: 2,
          closed_at: "2026-07-02T00:00:00Z",
        })}
      />,
    );
    expect(screen.getByText("TP")).toBeInTheDocument();
    expect(screen.getByText("R-Multiple").nextSibling).toHaveTextContent("2.00");
  });

  it("renders notes only when present", () => {
    const { rerender } = render(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.queryByText("Notes")).not.toBeInTheDocument();

    rerender(<TradeSummaryCard trade={buildTrade({ notes: "Waited for confirmation." })} />);
    expect(screen.getByText("Notes")).toBeInTheDocument();
    expect(screen.getByText("Waited for confirmation.")).toBeInTheDocument();
  });
});
