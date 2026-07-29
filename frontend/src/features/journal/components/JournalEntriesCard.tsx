import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable } from "../../../components/DataTable";
import { listJournalEntries } from "../api";
import { journalKeys } from "../queryKeys";
import type { JournalEntry } from "../types";
import { JournalEntryForm } from "./JournalEntryForm";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.3's `JournalEntriesCard` (scoped to
 * a Trade): "DataTable (or a simpler stacked list, given typically few
 * entries per trade)" + "'+ Journal Entry' → JournalEntryForm (Modal or
 * inline)." Lives in `features/journal/` (not `features/trading/`,
 * despite being embedded in `TradeDetailPage`) since it owns Journal's
 * own api/types — `TradeDetailPage` is a page, the one place in this
 * architecture permitted to compose another feature's component
 * directly (`eslint.config.js`'s `page` element, Sprint 5.1).
 */
export function JournalEntriesCard({ tradeId }: { tradeId: string }) {
  const [formOpen, setFormOpen] = useState(false);
  const [editingEntry, setEditingEntry] = useState<JournalEntry | null>(null);

  const { data } = useQuery({
    queryKey: journalKeys.list({ trade_id: tradeId }),
    queryFn: () => listJournalEntries({ trade_id: tradeId }),
  });

  const entries = data?.data ?? [];

  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">Journal</h2>
        <button type="button" onClick={() => setFormOpen(true)} className="text-sm text-accent">
          + Journal Entry
        </button>
      </div>

      <div className="mt-3">
        {entries.length === 0 ? (
          <p className="text-sm text-text-secondary">No journal entries for this trade yet.</p>
        ) : (
          <DataTable<JournalEntry>
            columns={[
              {
                key: "created_at",
                header: "Date",
                render: (entry) => new Date(entry.created_at).toLocaleString(),
              },
              {
                key: "content",
                header: "Content",
                render: (entry) =>
                  entry.content.length > 80 ? `${entry.content.slice(0, 80)}…` : entry.content,
              },
            ]}
            rows={entries}
            getRowKey={(entry) => entry.id}
            onRowClick={(entry) => setEditingEntry(entry)}
          />
        )}
      </div>

      <JournalEntryForm
        open={formOpen}
        onOpenChange={setFormOpen}
        mode={{ kind: "create-trade-scoped", tradeId }}
      />
      {editingEntry && (
        <JournalEntryForm
          open={editingEntry !== null}
          onOpenChange={(open) => {
            if (!open) {
              setEditingEntry(null);
            }
          }}
          mode={{ kind: "edit", entry: editingEntry }}
        />
      )}
    </div>
  );
}
