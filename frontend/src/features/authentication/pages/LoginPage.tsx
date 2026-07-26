import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../../../auth/AuthContext";
import { login } from "../api";
import { loginSchema, type LoginFormValues } from "../schemas";

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §5.7: "No sidebar entry; the only
 * unauthenticated pages in the app." Two separate routes (/login,
 * /register), per your approved decision — mirrors the two distinct
 * endpoints exactly.
 */
export function LoginPage() {
  const navigate = useNavigate();
  const { login: startSession } = useAuth();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const { mutate, isPending, error } = useMutation({
    mutationFn: login,
    onSuccess: (tokens) => {
      startSession(tokens.access_token, tokens.refresh_token);
      navigate("/");
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-base p-4">
      <form
        onSubmit={handleSubmit((values) => mutate(values))}
        className="w-full max-w-sm rounded border border-border bg-bg-surface p-6"
      >
        <h1 className="text-lg font-semibold text-text-primary">Sign in</h1>

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
            autoComplete="current-password"
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
          {isPending ? "Signing in…" : "Sign in"}
        </button>

        <p className="mt-4 text-center text-sm text-text-secondary">
          No account?{" "}
          <Link to="/register" className="text-accent">
            Register
          </Link>
        </p>
      </form>
    </div>
  );
}
