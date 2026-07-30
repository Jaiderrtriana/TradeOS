import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { LoginPage } from "./features/authentication/pages/LoginPage";
import { RegisterPage } from "./features/authentication/pages/RegisterPage";
import { ConfigurationPage } from "./features/configuration/pages/ConfigurationPage";
import { DashboardPage } from "./features/dashboard/pages/DashboardPage";
import { EvaluationPage } from "./features/evaluation/pages/EvaluationPage";
import { JournalEntryDetailPage } from "./features/journal/pages/JournalEntryDetailPage";
import { JournalListPage } from "./features/journal/pages/JournalListPage";
import { MistakesRankingPage } from "./features/mistakes/pages/MistakesRankingPage";
import { PlaybookPage } from "./features/playbook/pages/PlaybookPage";
import { PreferencesPage } from "./features/settings/pages/PreferencesPage";
import { TradeDetailPage } from "./features/trading/pages/TradeDetailPage";
import { TradesListPage } from "./features/trading/pages/TradesListPage";
import { RuleExplorerPage } from "./features/trading/pages/RuleExplorerPage";
import { AppShell } from "./layout/AppShell";

/**
 * Statistics is lazy-loaded, unlike every other route here (Sprint 6.2):
 * it is the first feature to pull in Recharts (`TRADEOS_TECHNICAL_STACK.md`
 * §6.8, mandatory), which alone pushed the single production bundle past
 * Vite's 500kB warning threshold. `TRADEOS_FRONTEND_BLUEPRINT.md` §2.4/§16
 * already call for per-feature code splitting — this is the first route
 * with a large enough feature-specific dependency to make that concretely
 * worth doing (`import()`-based, Vite's own recommended fix). Retrofitting
 * every other existing route is a separate, out-of-scope change.
 */
const StatisticsPage = lazy(() =>
  import("./features/statistics/pages/StatisticsPage").then((module) => ({
    default: module.StatisticsPage,
  })),
);

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
        <Route path="/trades" element={<TradesListPage />} />
        <Route path="/trades/:tradeId" element={<TradeDetailPage />} />
        <Route path="/trades/:tradeId/evaluation" element={<RuleExplorerPage />} />
        <Route path="/playbook" element={<PlaybookPage />} />
        <Route path="/journal" element={<JournalListPage />} />
        <Route path="/journal/:entryId" element={<JournalEntryDetailPage />} />
        <Route
          path="/statistics"
          element={
            <Suspense fallback={<div className="p-6 text-sm text-text-secondary">Loading…</div>}>
              <StatisticsPage />
            </Suspense>
          }
        />
        <Route path="/mistakes" element={<MistakesRankingPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/configuration" element={<ConfigurationPage />} />
        <Route path="/settings" element={<PreferencesPage />} />
      </Route>
    </Routes>
  );
}
