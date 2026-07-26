import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { ApiError } from "../api/errors";
import { installErrorSimulationHook } from "../test-support/errorSimulation";
import { ErrorBanner } from "./ErrorBanner";

/**
 * The one shared error path (TRADEOS_FRONTEND_BLUEPRINT.md §2.8): any
 * future feature module reports a failed request here via
 * useErrorReporter(), and ErrorBanner is rendered exactly once, from this
 * Provider — never re-implemented per page.
 */
interface ErrorContextValue {
  reportError: (error: ApiError) => void;
  clearError: () => void;
}

const ErrorContext = createContext<ErrorContextValue | null>(null);

export function ErrorProvider({ children }: { children: ReactNode }) {
  const [error, setError] = useState<ApiError | null>(null);

  const reportError = useCallback((nextError: ApiError) => setError(nextError), []);
  const clearError = useCallback(() => setError(null), []);

  const value = useMemo(() => ({ reportError, clearError }), [reportError, clearError]);

  useEffect(() => {
    installErrorSimulationHook(reportError);
  }, [reportError]);

  return (
    <ErrorContext.Provider value={value}>
      {error && <ErrorBanner error={error} onDismiss={clearError} />}
      {children}
    </ErrorContext.Provider>
  );
}

export function useErrorReporter(): ErrorContextValue {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error("useErrorReporter must be used within an ErrorProvider");
  }
  return context;
}
