import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { DashboardTrade } from "../types";
import { RecentTradesPreview } from "./RecentTradesPreview";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

function buildTrade(overrides: Partial<DashboardTrade> = {}): DashboardTrade {
  return {
    id: "trade-1",
    market: "EURUSD",
    direction: "long",
    status: "open",
    result: null,
    r_multiple: 1.5,
    entered_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("RecentTradesPreview", () => {
  it("shows the empty state when there are no trades", () => {
    render(
      <MemoryRouter>
        <RecentTradesPreview trades={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/No trades yet/)).toBeInTheDocument();
  });

  it("renders each trade's market, direction, and status", () => {
    render(
      <MemoryRouter>
        <RecentTradesPreview trades={[buildTrade()]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("EURUSD")).toBeInTheDocument();
    expect(screen.getByText("Long")).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText("1.50 R")).toBeInTheDocument();
  });

  it("navigates to the trade's detail page when a row is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <RecentTradesPreview trades={[buildTrade({ id: "trade-42" })]} />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button"));
    expect(navigateMock).toHaveBeenCalledWith("/trades/trade-42");
  });
});
