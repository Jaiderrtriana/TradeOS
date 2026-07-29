import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { DataTable } from "../../../components/DataTable";
import { listJournalEntries } from "../api";
import { JournalEntryForm } from "../components/JournalEntryForm";
import { journalKeys } from "../queryKeys";
import type { JournalEntry, ListJournalEntriesFilters } from "../types";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's "Journal List" row: "Browse
 * reflections... Filterable by Trade or date range, matching the API
 * exactly." §6.10's period-scoped flow: "Journal module → Journal List
 * → '+ New Entry' → period-scoped form." No dedicated Trade picker here
 * — trade-scoped entries are created from Trade Detail
 * (`JournalEntriesCard`); this page's own filters mirror `GET
 * /journal-entries`'s date-range filter.
 */
export function JournalListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<ListJournalEntriesFilters>({});
  const [formOpen, setFormOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: journalKeys.list(filters),
    queryFn: () => listJournalEntries(filters),
  });

  const entries = data?.data ?? [];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-text-primary">Journal</h1>
        <button
          type="button"
          onClick={() => setFormOpen(true)}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary"
        >
          + New Entry
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="period_start" className="mb-1 block text-sm text-text-secondary">
            From
          </label>
          <input
            id="period_start"
            type="date"
            value={filters.period_start ?? ""}
            onChange={(event) =>
              setFilters((previous) => ({
                ...previous,
                period_start: event.target.value || undefined,
                cursor: undefined,
              }))
            }
            className="rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
          />
        </div>
        <div>
          <label htmlFor="period_end" className="mb-1 block text-sm text-text-secondary">
            To
          </label>
          <input
            id="period_end"
            type="date"
            value={filters.period_end ?? ""}
            onChange={(event) =>
              setFilters((previous) => ({
                ...previous,
                period_end: event.target.value || undefined,
                cursor: undefined,
              }))
            }
            className="rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
          />
        </div>
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : entries.length === 0 ? (
          <p className="text-sm text-text-secondary">
            No journal entries yet — use “+ New Entry” to write your first reflection.
          </p>
        ) : (
          <DataTable<JournalEntry>
            columns={[
              {
                key: "reference",
                header: "Trade / Period",
                render: (entry) =>
                  entry.trade_id ? `Trade #${entry.trade_id}` : `${entry.period_start} – ${entry.period_end}`,
              },
              {
                key: "content",
                header: "Content",
                render: (entry) =>
                  entry.content.length > 100 ? `${entry.content.slice(0, 100)}…` : entry.content,
              },
              {
                key: "created_at",
                header: "Created",
                render: (entry) => new Date(entry.created_at).toLocaleString(),
              },
            ]}
            rows={entries}
            getRowKey={(entry) => entry.id}
            onRowClick={(entry) => navigate(`/journal/${entry.id}`)}
          />
        )}
      </div>

      <JournalEntryForm open={formOpen} onOpenChange={setFormOpen} mode={{ kind: "create-period-scoped" }} />
    </div>
  );
}
