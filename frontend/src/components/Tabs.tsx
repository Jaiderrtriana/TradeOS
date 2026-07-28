import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

/**
 * Shared Tabs — TRADEOS_FRONTEND_BLUEPRINT.md §4.2: "Within a module,
 * sub-views are tabs, not separate sidebar entries." First consumer is
 * Configuration (Scoring Versions / Catalogs Management); Statistics
 * (Overview / By Dimension / Rolling) reuses this same component later.
 * TRADEOS_TECHNICAL_STACK.md §6.5: Radix supplies "correct ARIA roles on a
 * Tabs component" — the exact reason it was selected over a hand-rolled
 * implementation.
 *
 * `value`/`onValueChange` (Sprint 4.4): optional controlled mode, added
 * for Trade Entry's Simple/Pro toggle (`TRADEOS_FRONTEND_BLUEPRINT.md`
 * §5.7), which needs the active tab as external state (submission logic
 * reads it) — every earlier consumer stays uncontrolled via
 * `defaultValue` alone, unaffected.
 */
export interface TabItem {
  value: string;
  label: string;
  content: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function Tabs({ items, defaultValue, value, onValueChange }: TabsProps) {
  return (
    <RadixTabs.Root defaultValue={defaultValue} value={value} onValueChange={onValueChange}>
      <RadixTabs.List className="flex gap-1 border-b border-border" aria-label="Sections">
        {items.map((item) => (
          <RadixTabs.Trigger
            key={item.value}
            value={item.value}
            className="px-4 py-2 text-sm text-text-secondary outline-none data-[state=active]:border-b-2 data-[state=active]:border-accent data-[state=active]:text-text-primary"
          >
            {item.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {items.map((item) => (
        <RadixTabs.Content key={item.value} value={item.value} className="pt-4">
          {item.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}
