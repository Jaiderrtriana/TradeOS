import { NavLink } from "react-router-dom";

import { NAV_GROUPS, RESERVED_INACTIVE_NAV_ITEM, SETTINGS_NAV_ITEM } from "./navigation";

const linkClassName = ({ isActive }: { isActive: boolean }) =>
  `block rounded border-l-2 px-3 py-1.5 text-sm ${
    isActive
      ? "border-accent bg-bg-overlay text-text-primary"
      : "border-transparent text-text-secondary hover:bg-bg-surface hover:text-text-primary"
  }`;

export function Sidebar() {
  return (
    <nav aria-label="Primary" className="flex h-full w-56 flex-col gap-6 bg-bg-base p-4">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="px-3 text-xs font-semibold uppercase tracking-wide text-text-muted">
            {group.label}
          </p>
          <ul className="mt-2 flex flex-col gap-0.5">
            {group.items.map((item) => (
              <li key={item.path}>
                <NavLink to={item.path} className={linkClassName} end={item.path === "/"}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}

      <div>
        <ul className="flex flex-col gap-0.5">
          <li>
            <NavLink to={SETTINGS_NAV_ITEM.path} className={linkClassName}>
              {SETTINGS_NAV_ITEM.label}
            </NavLink>
          </li>
          <li>
            <span
              aria-disabled="true"
              className="block cursor-not-allowed rounded px-3 py-1.5 text-sm text-text-muted"
            >
              {RESERVED_INACTIVE_NAV_ITEM.label}
            </span>
          </li>
        </ul>
      </div>
    </nav>
  );
}
