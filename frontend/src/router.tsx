import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./features/authentication/pages/LoginPage";
import { RegisterPage } from "./features/authentication/pages/RegisterPage";
import { ConfigurationPage } from "./features/configuration/pages/ConfigurationPage";
import { DashboardPage } from "./features/dashboard/pages/DashboardPage";
import { EvaluationPage } from "./features/evaluation/pages/EvaluationPage";
import { JournalPage } from "./features/journal/pages/JournalPage";
import { MistakesPage } from "./features/mistakes/pages/MistakesPage";
import { PlaybookPage } from "./features/playbook/pages/PlaybookPage";
import { PreferencesPage } from "./features/settings/pages/PreferencesPage";
import { StatisticsPage } from "./features/statistics/pages/StatisticsPage";
import { TradingPage } from "./features/trading/pages/TradingPage";
import { AppShell } from "./layout/AppShell";

/**
 * Routing — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 1.2: /login and
 * /register are two separate routes (approved decision), neither has a
 * sidebar entry (TRADEOS_FRONTEND_BLUEPRINT.md §5.7) and both render
 * outside AppShell. Every other route now requires an active session
 * (ProtectedRoute) — a first "fully vertical" slice, per the sprint's own
 * deliverable framing.
 */
export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/trades" element={<TradingPage />} />
        <Route path="/playbook" element={<PlaybookPage />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/statistics" element={<StatisticsPage />} />
        <Route path="/mistakes" element={<MistakesPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/configuration" element={<ConfigurationPage />} />
        <Route path="/settings" element={<PreferencesPage />} />
      </Route>
    </Routes>
  );
}
