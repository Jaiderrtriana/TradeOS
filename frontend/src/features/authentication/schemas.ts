import { z } from "zod";

/**
 * Mirrors app/modules/identity/presentation/schemas.py field-for-field
 * (TRADEOS_API_SPECIFICATION.md §6.1). The password minimum (8) matches
 * the backend's own documented implementation default (CHANGELOG.md,
 * Sprint 1.1/1.2) — not a literal spec value, since §9 states none.
 */
export const loginSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});
export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.string().email("Enter a valid email address."),
  password: z.string().min(8, "Password must be at least 8 characters."),
});
export type RegisterFormValues = z.infer<typeof registerSchema>;
