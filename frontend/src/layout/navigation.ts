/**
 * Sidebar structure — TRADEOS_FRONTEND_BLUEPRINT.md §4.1, grouped by
 * day-to-day usage frequency, not Bounded Context alphabetical order.
 * Single source of truth consumed by both Sidebar.tsx and router.tsx so
 * the two can never drift out of sync.
 */
export interface NavItem {
  label: string;
  path: string;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", path: "/" },
      { label: "Trades", path: "/trades" },
      { label: "Playbook", path: "/playbook" },
      { label: "Journal", path: "/journal" },
    ],
  },
  {
    label: "Analytics",
    items: [
      { label: "Statistics", path: "/statistics" },
      { label: "Mistakes", path: "/mistakes" },
      { label: "Evaluation", path: "/evaluation" },
    ],
  },
  {
    label: "Configuration",
    items: [{ label: "Scoring & Catalogs", path: "/configuration" }],
  },
];

/**
 * Settings is a confirmed module (§3) with no explicit sidebar placement
 * in §4.1's own grouping list — kept as its own minimal group rather than
 * silently folded into one of the three named groups above.
 */
export const SETTINGS_NAV_ITEM: NavItem = { label: "Settings", path: "/settings" };

/**
 * §4.1: "Reserved, visually present but inactive: AI Coach — shown so the
 * information architecture doesn't need to change when it ships, not
 * because it is usable today." Not a route — no confirmed module or page
 * exists for it (§3, "Not confirmed").
 */
export const RESERVED_INACTIVE_NAV_ITEM = { label: "AI Coach" };
