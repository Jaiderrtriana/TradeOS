import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { debounce } from "./debounce";

describe("debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("collapses rapid, repeated calls into exactly one invocation", () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 500);

    debounced("a");
    vi.advanceTimersByTime(100);
    debounced("b");
    vi.advanceTimersByTime(100);
    debounced("c");
    vi.advanceTimersByTime(499);
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
    // Only the *last* call's arguments survive -- the same guarantee that
    // makes rapid multi-field edits race-condition-safe: whichever state
    // was current when the user paused is what gets sent.
    expect(fn).toHaveBeenCalledWith("c");
  });

  it("fires again after a quiet period, once per quiet period", () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 500);

    debounced("first");
    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(1);

    debounced("second");
    vi.advanceTimersByTime(500);
    expect(fn).toHaveBeenCalledTimes(2);
    expect(fn).toHaveBeenLastCalledWith("second");
  });

  it("cancel() prevents a pending call from firing", () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 500);

    debounced("a");
    debounced.cancel();
    vi.advanceTimersByTime(1000);

    expect(fn).not.toHaveBeenCalled();
  });
});
