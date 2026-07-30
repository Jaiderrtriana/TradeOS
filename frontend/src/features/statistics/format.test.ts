import { describe, expect, it } from "vitest";

import { formatPnl, formatR, formatRatioAsPercent, formatScore } from "./format";

describe("formatRatioAsPercent", () => {
  it("renders a raw 0-1 ratio as a percentage", () => {
    expect(formatRatioAsPercent(0.5)).toBe("50.0%");
  });

  it("renders null as an em dash", () => {
    expect(formatRatioAsPercent(null)).toBe("—");
  });
});

describe("formatR", () => {
  it("renders a negative R-multiple with two decimals", () => {
    expect(formatR(-1)).toBe("-1.00");
  });

  it("renders null as an em dash", () => {
    expect(formatR(null)).toBe("—");
  });
});

describe("formatPnl", () => {
  it("renders zero with two decimals", () => {
    expect(formatPnl(0)).toBe("0.00");
  });
});

describe("formatScore", () => {
  it("renders a zero score, distinct from null", () => {
    expect(formatScore(0)).toBe("0.0");
  });

  it("renders null as an em dash", () => {
    expect(formatScore(null)).toBe("—");
  });
});
