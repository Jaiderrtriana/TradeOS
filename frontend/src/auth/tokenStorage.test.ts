import { afterEach, beforeAll, describe, expect, it } from "vitest";

import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "./tokenStorage";

/**
 * Vitest's "node" environment (TRADEOS_TECHNICAL_STACK.md §10 names
 * Vitest, not jsdom) has no `localStorage` global. A minimal in-memory
 * mock avoids adding jsdom as a new dependency for one file's tests —
 * this test only needs get/set/remove/clear, the same surface tokenStorage
 * itself uses.
 */
beforeAll(() => {
  const store = new Map<string, string>();
  globalThis.localStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    removeItem: (key: string) => void store.delete(key),
    clear: () => store.clear(),
    key: (index: number) => Array.from(store.keys())[index] ?? null,
    get length() {
      return store.size;
    },
  } satisfies Storage;
});

afterEach(() => {
  clearTokens();
});

describe("tokenStorage", () => {
  it("returns null for both tokens when nothing is stored", () => {
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("persists both tokens after setTokens", () => {
    setTokens("access-abc", "refresh-xyz");
    expect(getAccessToken()).toBe("access-abc");
    expect(getRefreshToken()).toBe("refresh-xyz");
  });

  it("clears both tokens after clearTokens", () => {
    setTokens("access-abc", "refresh-xyz");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});
