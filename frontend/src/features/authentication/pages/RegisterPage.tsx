import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { registerAccount } from "../api";
import { registerSchema, type RegisterFormValues } from "../schemas";

/**
 * TRADEOS_API_SPECIFICATION.md §6.1: register does not return an access
 * token — "the client must still log in" as a deliberately separate step
 * — so success here navigates to /login, never straight into a session.
 */
export function RegisterPage() {
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const { mutate, isPending, error } = useMutation({
    mutationFn: registerAccount,
    onSuccess: () => navigate("/login"),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base p-4">
      <form
        onSubmit={handleSubmit((values) => mutate(values))}
        className="w-full max-w-sm rounded border border-border bg-bg-surface p-6"
      >
        <h1 className="text-lg font-semibold text-text-primary">Create an account</h1>

        <div className="mt-4">
          <label htmlFor="email" className="block text-sm text-text-secondary">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className="mt-1 w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("email")}
          />
          {errors.email && <p className="mt-1 text-xs text-danger">{errors.email.message}</p>}
        </div>

        <div className="mt-4">
          <label htmlFor="password" className="block text-sm text-text-secondary">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            className="mt-1 w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("password")}
          />
          {errors.password && <p className="mt-1 text-xs text-danger">{errors.password.message}</p>}
        </div>

        {error && <p className="mt-4 text-sm text-danger">{error.message}</p>}

        <button
          type="submit"
          disabled={isPending}
          className="mt-6 w-full rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
        >
          {isPending ? "Creating account…" : "Create account"}
        </button>

        <p className="mt-4 text-center text-sm text-text-secondary">
          Already have an account?{" "}
          <Link to="/login" className="text-accent">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  );
}
