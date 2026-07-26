import { Route, Routes } from "react-router-dom";

import { AuthenticationPage } from "./features/authentication/pages/AuthenticationPage";
import { ConfigurationPage } from "./features/configuration/pages/ConfigurationPage";
import { DashboardPage } from "./features/dashboard/pages/DashboardPage";
import { EvaluationPage } from "./features/evaluation/pages/EvaluationPage";
import { JournalPage } from "./features/journal/pages/JournalPage";
import { MistakesPage } from "./features/mistakes/pages/MistakesPage";
import { PlaybookPage } from "./features/playbook/pages/PlaybookPage";
import { SettingsPage } from "./features/settings/pages/SettingsPage";
import { StatisticsPage } from "./features/statistics/pages/StatisticsPage";
import { TradingPage } from "./features/trading/pages/TradingPage";
import { AppShell } from "./layout/AppShell";

/**
 * Routing skeleton — TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 0.3: one
 * routable placeholder per confirmed frontend module
 * (TRADEOS_FRONTEND_BLUEPRINT.md §3). Authentication has no sidebar entry
 * (§5.7) and renders outside AppShell; every other confirmed module is
 * nested under it.
 */
export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<AuthenticationPage />} />
      <Route element={<AppShell />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/trades" element={<TradingPage />} />
        <Route path="/playbook" element={<PlaybookPage />} />
        <Route path="/journal" element={<JournalPage />} />
        <Route path="/statistics" element={<StatisticsPage />} />
        <Route path="/mistakes" element={<MistakesPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/configuration" element={<ConfigurationPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
