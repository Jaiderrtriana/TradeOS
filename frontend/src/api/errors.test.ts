import { describe, expect, it } from "vitest";

import { ApiError, networkError, parseApiError, UNKNOWN_ERROR_CODE } from "./errors";

describe("parseApiError", () => {
  it("normalizes a well-formed error envelope (TRADEOS_API_SPECIFICATION.md §8)", () => {
    const envelope = {
      error: {
        code: "UNAUTHENTICATED",
        message: "Authentication required.",
        details: [{ field: "authorization", issue: "missing" }],
        trace_id: "abc-123",
        timestamp: "2026-07-25T00:00:00Z",
      },
    };

    const result = parseApiError(401, envelope);

    expect(result).toBeInstanceOf(ApiError);
    expect(result.status).toBe(401);
    expect(result.code).toBe("UNAUTHENTICATED");
    expect(result.message).toBe("Authentication required.");
    expect(result.details).toEqual([{ field: "authorization", issue: "missing" }]);
    expect(result.traceId).toBe("abc-123");
  });

  it("falls back to UNKNOWN_ERROR_CODE when the body doesn't match the envelope shape", () => {
    const result = parseApiError(502, "<html>Bad Gateway</html>");

    expect(result.code).toBe(UNKNOWN_ERROR_CODE);
    expect(result.status).toBe(502);
    expect(result.traceId).toBeNull();
  });

  it("falls back to UNKNOWN_ERROR_CODE when the body is null", () => {
    const result = parseApiError(500, null);

    expect(result.code).toBe(UNKNOWN_ERROR_CODE);
  });

  it("falls back when error.code or error.message is missing", () => {
    const result = parseApiError(422, { error: { details: [] } });

    expect(result.code).toBe(UNKNOWN_ERROR_CODE);
  });
});

describe("networkError", () => {
  it("produces a client-side ApiError with no HTTP status", () => {
    const result = networkError();

    expect(result).toBeInstanceOf(ApiError);
    expect(result.status).toBeNull();
    expect(result.code).toBe("NETWORK_ERROR");
  });
});
