import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";

/**
 * The application shell — TRADEOS_FRONTEND_BLUEPRINT.md §2.2's outer layer,
 * wrapping every authenticated route in Sidebar + a top bar placeholder.
 * The Authentication module's routes (Login/Register) render outside this
 * shell entirely (§5.7: "No sidebar entry").
 */
export function AppShell() {
  return (
    <div className="flex h-screen bg-bg-base text-text-primary">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="border-b border-border px-6 py-3">
          <span className="text-sm font-medium text-text-secondary">TradeOS</span>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
