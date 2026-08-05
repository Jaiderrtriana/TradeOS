import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DashboardMistakeRankingEntry } from "../types";
import { TopMistakesPreview } from "./TopMistakesPreview";

function buildMistake(
  overrides: Partial<DashboardMistakeRankingEntry> = {},
): DashboardMistakeRankingEntry {
  return {
    catalog_entry_id: "tag-1",
    name: "FOMO",
    is_active: true,
    frequency: 3,
    total_cost_r: -2.5,
    priority: 1,
    ...overrides,
  };
}

describe("TopMistakesPreview", () => {
  it("shows the empty state when there are no mistakes", () => {
    render(<TopMistakesPreview mistakes={[]} />);
    expect(screen.getByText("No mistakes tagged yet.")).toBeInTheDocument();
  });

  it("renders each mistake's name, frequency, and cost", () => {
    render(<TopMistakesPreview mistakes={[buildMistake()]} />);
    expect(screen.getByText("FOMO")).toBeInTheDocument();
    expect(screen.getByText("3× · -2.50 R")).toBeInTheDocument();
  });
});
