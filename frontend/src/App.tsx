import { BrowserRouter } from "react-router-dom";

import { ErrorProvider } from "./components/ErrorContext";
import { AppRouter } from "./router";

export function App() {
  return (
    <BrowserRouter>
      {/* ErrorProvider wraps the whole router so ErrorBanner renders from
          one place regardless of which route is active — including
          Authentication, which sits outside AppShell. */}
      <ErrorProvider>
        <AppRouter />
      </ErrorProvider>
    </BrowserRouter>
  );
}
