import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { ErrorProvider } from "./components/ErrorContext";
import { AppRouter } from "./router";

// TRADEOS_TECHNICAL_STACK.md §6.3: TanStack Query is the server-state
// layer, first genuinely used in Sprint 1.2 (GET /preferences). One
// QueryClient instance for the whole app.
const queryClient = new QueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/* ErrorProvider wraps the whole router so ErrorBanner renders from
            one place regardless of which route is active — including
            Authentication, which sits outside AppShell. */}
        <ErrorProvider>
          <AuthProvider>
            <AppRouter />
          </AuthProvider>
        </ErrorProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
