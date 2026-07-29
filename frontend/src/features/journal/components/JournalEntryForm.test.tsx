import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ErrorProvider } from "../../../components/ErrorContext";
import type { JournalEntry } from "../types";
import { JournalEntryForm } from "./JournalEntryForm";

/**
 * Component-tier scope, deliberately: form structure, field visibility
 * per mode, and client-side validation rendering only — no assertion on
 * a real `POST`/`PATCH` actually persisting, which is an E2E concern
 * (`e2e/journal.spec.ts`), same documented boundary as
 * `VirtualizedDataTable.test.tsx`.
 */
function renderWithProviders(ui: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ErrorProvider>{ui}</ErrorProvider>
    </QueryClientProvider>,
  );
}

const entry: JournalEntry = {
  id: "entry-1",
  trade_id: "trade-1",
  period_start: null,
  period_end: null,
  content: "Original content.",
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
};

describe("JournalEntryForm", () => {
  it("renders only a content field in trade-scoped create mode", () => {
    renderWithProviders(
      <JournalEntryForm
        open
        onOpenChange={() => {}}
        mode={{ kind: "create-trade-scoped", tradeId: "trade-1" }}
      />,
    );
    expect(screen.getByLabelText("Content")).toBeInTheDocument();
    expect(screen.queryByLabelText("Period Start")).not.toBeInTheDocument();
  });

  it("renders period_start/period_end plus content in period-scoped create mode", () => {
    renderWithProviders(
      <JournalEntryForm open onOpenChange={() => {}} mode={{ kind: "create-period-scoped" }} />,
    );
    expect(screen.getByLabelText("Period Start")).toBeInTheDocument();
    expect(screen.getByLabelText("Period End")).toBeInTheDocument();
  });

  it("pre-fills content and shows the reference as read-only text in edit mode", () => {
    renderWithProviders(<JournalEntryForm open onOpenChange={() => {}} mode={{ kind: "edit", entry }} />);
    expect(screen.getByLabelText("Content")).toHaveValue("Original content.");
    expect(screen.getByText(/Attached to trade #trade-1/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Period Start")).not.toBeInTheDocument();
  });

  it("shows a period reference, not a trade reference, when editing a period-scoped entry", () => {
    renderWithProviders(
      <JournalEntryForm
        open
        onOpenChange={() => {}}
        mode={{
          kind: "edit",
          entry: { ...entry, trade_id: null, period_start: "2026-07-01", period_end: "2026-07-07" },
        }}
      />,
    );
    expect(screen.getByText(/Period: 2026-07-01 – 2026-07-07/)).toBeInTheDocument();
  });

  it("shows a validation error when submitting empty content", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <JournalEntryForm
        open
        onOpenChange={() => {}}
        mode={{ kind: "create-trade-scoped", tradeId: "trade-1" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save Entry" }));
    expect(await screen.findByText("Enter some content.")).toBeInTheDocument();
  });
});
