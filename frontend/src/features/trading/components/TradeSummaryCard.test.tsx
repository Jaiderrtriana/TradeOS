import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { TradeDetail } from "../types";
import { TradeSummaryCard } from "./TradeSummaryCard";

/** `TradeSummaryCard` resolves its display timezone via
 * `usePreferencesTimezone` (Sprint 4, OQ-7), which needs a QueryClient in
 * context — same `renderWithProviders` pattern as `JournalEntryForm.test.tsx`.
 * The `/preferences` fetch it triggers is never mocked here: it rejects in
 * this jsdom environment, `usePreferencesTimezone` falls back to the
 * browser-detected zone exactly as it would for a real logged-out/loading
 * state, and no test below asserts on the exact formatted string — only on
 * presence/absence — so that fallback is irrelevant to what's being tested.
 */
function renderWithProviders(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

const EMPTY_ENGINE = { score: null, grade: null, breakdown: [] };
const EMPTY_BIAS = { score: null, breakdown: [] };

function buildTrade(overrides: Partial<TradeDetail> = {}): TradeDetail {
  return {
    id: "trade-1",
    market: "EURUSD",
    direction: "long",
    status: "open",
    entry_price: 100,
    stop_loss: 95,
    take_profit: null,
    exit_price: null,
    size: 1,
    margin_used: null,
    leverage: "",
    result: null,
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
    roi_percent: null,
    pnl_percent: null,
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
  it("renders the market as a heading and the direction/status badges", () => {
    renderWithProviders(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.getByRole("heading", { name: "EURUSD" })).toBeInTheDocument();
    expect(screen.getByText("Long")).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
  });

  it("does not render a result badge while result is null", () => {
    renderWithProviders(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.queryByText("TP")).not.toBeInTheDocument();
    expect(screen.queryByText("SL")).not.toBeInTheDocument();
    expect(screen.queryByText("BE")).not.toBeInTheDocument();
  });

  it("shows an em dash for every not-yet-computed field on an open trade", () => {
    renderWithProviders(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.getByText("Exit Price").nextSibling).toHaveTextContent("—");
    expect(screen.getByText("R-Multiple").nextSibling).toHaveTextContent("—");
  });

  it("shows an em dash for entry facts on a planned trade", () => {
    renderWithProviders(
      <TradeSummaryCard
        trade={buildTrade({
          status: "planned",
          entry_price: null,
          stop_loss: null,
          entered_at: null,
          evaluation: null,
        })}
      />,
    );
    expect(screen.getByText("PLANNED")).toBeInTheDocument();
    expect(screen.getByText("Entry Price").nextSibling).toHaveTextContent("—");
    expect(screen.getByText("Stop Loss").nextSibling).toHaveTextContent("—");
    expect(screen.getByText("Entered At").nextSibling).toHaveTextContent("—");
  });

  it("renders computed values once the trade is closed", () => {
    renderWithProviders(
      <TradeSummaryCard
        trade={buildTrade({
          status: "closed",
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
    const { rerender } = renderWithProviders(<TradeSummaryCard trade={buildTrade()} />);
    expect(screen.queryByText("Notes")).not.toBeInTheDocument();

    rerender(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <TradeSummaryCard trade={buildTrade({ notes: "Waited for confirmation." })} />
      </QueryClientProvider>,
    );
    expect(screen.getByText("Notes")).toBeInTheDocument();
    expect(screen.getByText("Waited for confirmation.")).toBeInTheDocument();
  });
});
