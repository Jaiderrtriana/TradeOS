import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScorePanel } from "./ScorePanel";

describe("ScorePanel", () => {
  it("renders a graded engine's ScoreRing and breakdown rows", () => {
    render(
      <ScorePanel
        label="Confidence"
        result={{
          score: 82,
          grade: "B",
          breakdown: [
            {
              criterion_id: "confidence.dxy",
              criterion_name: "DXY Alignment",
              raw_value: "Yes",
              normalized_value: 100,
              weight: 0.5,
              contribution: 50,
            },
          ],
        }}
      />,
    );
    expect(screen.getByTestId("score-ring-confidence")).toHaveTextContent("82");
    expect(screen.getByText("DXY Alignment")).toBeInTheDocument();
    expect(screen.getByText("50.00")).toBeInTheDocument();
  });

  it("renders the empty-breakdown message when no criteria contributed", () => {
    render(<ScorePanel label="Bias" result={{ score: 0, breakdown: [] }} />);
    expect(screen.getByText("No criteria contributed to this score.")).toBeInTheDocument();
  });

  it("renders a Bias (signed) result without a grade badge", () => {
    render(<ScorePanel label="Bias" result={{ score: -2.5, breakdown: [] }} />);
    expect(screen.getByText("signed")).toBeInTheDocument();
  });
});
