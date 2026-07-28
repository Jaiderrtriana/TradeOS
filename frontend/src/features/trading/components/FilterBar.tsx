import { useQuery } from "@tanstack/react-query";

import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { catalogEntryKeys, listCatalogEntries } from "../../../shared/catalogEntries";
import type { ListTradesFilters } from "../types";

const DIRECTION_OPTIONS = [
  { value: "", label: "Any direction" },
  { value: "long", label: "Long" },
  { value: "short", label: "Short" },
];

const RESULT_OPTIONS = [
  { value: "", label: "Any result" },
  { value: "open", label: "Open" },
  { value: "tp", label: "Take Profit" },
  { value: "sl", label: "Stop Loss" },
  { value: "be", label: "Break Even" },
];

export interface FilterBarProps {
  filters: ListTradesFilters;
  onChange: (filters: ListTradesFilters) => void;
}

function useCatalogOptions(kind: string) {
  const { data } = useQuery({
    queryKey: catalogEntryKeys.list(kind),
    queryFn: () => listCatalogEntries(kind),
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });
  return (data ?? [])
    .filter((entry) => entry.is_active)
    .map((entry) => ({ value: entry.id, label: entry.name }));
}

/**
 * Trades List filters — `TRADEOS_FRONTEND_BLUEPRINT.md` §11: "Direction,
 * Result, date range, dimension fields — exactly the API's filter set."
 * No filter here that `GET /trades` doesn't itself accept.
 */
export function FilterBar({ filters, onChange }: FilterBarProps) {
  const strategyOptions = useCatalogOptions("strategy");
  const setupOptions = useCatalogOptions("setup");
  const sessionOptions = useCatalogOptions("session");

  function set<K extends keyof ListTradesFilters>(key: K, value: ListTradesFilters[K]) {
    onChange({ ...filters, [key]: value, cursor: undefined });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div>
        <p className="mb-1 text-sm text-text-secondary">Direction</p>
        <Select
          value={filters.direction ?? ""}
          onValueChange={(value) => set("direction", value === "" ? undefined : (value as "long" | "short"))}
          options={DIRECTION_OPTIONS}
          aria-label="Filter by direction"
        />
      </div>
      <div>
        <p className="mb-1 text-sm text-text-secondary">Result</p>
        <Select
          value={filters.result ?? ""}
          onValueChange={(value) =>
            set("result", value === "" ? undefined : (value as ListTradesFilters["result"]))
          }
          options={RESULT_OPTIONS}
          aria-label="Filter by result"
        />
      </div>
      <div>
        <label htmlFor="entered_after" className="mb-1 block text-sm text-text-secondary">
          Entered after
        </label>
        <input
          id="entered_after"
          type="date"
          value={filters.entered_after?.slice(0, 10) ?? ""}
          onChange={(event) =>
            set("entered_after", event.target.value ? `${event.target.value}T00:00:00Z` : undefined)
          }
          className="rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
        />
      </div>
      <div>
        <label htmlFor="entered_before" className="mb-1 block text-sm text-text-secondary">
          Entered before
        </label>
        <input
          id="entered_before"
          type="date"
          value={filters.entered_before?.slice(0, 10) ?? ""}
          onChange={(event) =>
            set("entered_before", event.target.value ? `${event.target.value}T23:59:59Z` : undefined)
          }
          className="rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
        />
      </div>
      <div>
        <p className="mb-1 text-sm text-text-secondary">Strategy</p>
        <Select
          value={filters.strategy_id ?? ""}
          onValueChange={(value) => set("strategy_id", value === "" ? undefined : value)}
          options={[{ value: "", label: "Any strategy" }, ...strategyOptions]}
          aria-label="Filter by strategy"
        />
      </div>
      <div>
        <p className="mb-1 text-sm text-text-secondary">Setup</p>
        <Select
          value={filters.setup_id ?? ""}
          onValueChange={(value) => set("setup_id", value === "" ? undefined : value)}
          options={[{ value: "", label: "Any setup" }, ...setupOptions]}
          aria-label="Filter by setup"
        />
      </div>
      <div>
        <p className="mb-1 text-sm text-text-secondary">Session</p>
        <Select
          value={filters.session_id ?? ""}
          onValueChange={(value) => set("session_id", value === "" ? undefined : value)}
          options={[{ value: "", label: "Any session" }, ...sessionOptions]}
          aria-label="Filter by session"
        />
      </div>
    </div>
  );
}
