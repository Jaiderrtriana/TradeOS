import { describe, expect, it } from "vitest";

import { loginSchema, registerSchema } from "./schemas";

describe("loginSchema", () => {
  it("accepts a valid email and non-empty password", () => {
    const result = loginSchema.safeParse({ email: "trader@example.com", password: "x" });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = loginSchema.safeParse({ email: "not-an-email", password: "x" });
    expect(result.success).toBe(false);
  });

  it("rejects an empty password", () => {
    const result = loginSchema.safeParse({ email: "trader@example.com", password: "" });
    expect(result.success).toBe(false);
  });
});

describe("registerSchema", () => {
  it("accepts a valid email and an 8+ character password", () => {
    const result = registerSchema.safeParse({
      email: "trader@example.com",
      password: "password123",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a password shorter than 8 characters", () => {
    const result = registerSchema.safeParse({ email: "trader@example.com", password: "short" });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid email", () => {
    const result = registerSchema.safeParse({ email: "nope", password: "password123" });
    expect(result.success).toBe(false);
  });
});
