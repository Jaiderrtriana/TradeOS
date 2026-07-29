import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ApiError } from "../../../api/errors";
import { ConfirmDialog } from "../../../components/ConfirmDialog";
import { useErrorReporter } from "../../../components/ErrorContext";
import { deleteJournalEntry, getJournalEntry } from "../api";
import { JournalEntryForm } from "../components/JournalEntryForm";
import { journalKeys } from "../queryKeys";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's "Journal Entry Detail/Edit"
 * row: "Read/write one reflection... Reference type (Trade vs. period)
 * is immutable after creation, per the API — the UI must not offer to
 * change it." A `404` covers "doesn't exist" and "not yours" identically
 * (`TRADEOS_API_SPECIFICATION.md` §8), same convention as Trade Detail.
 */
export function JournalEntryDetailPage() {
  const { entryId } = useParams<{ entryId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [editOpen, setEditOpen] = useState(false);

  const {
    data: entry,
    isLoading,
    error,
  } = useQuery({
    queryKey: journalKeys.detail(entryId as string),
    queryFn: () => getJournalEntry(entryId as string),
    enabled: entryId !== undefined,
    retry: false,
  });

  const remove = useMutation({
    mutationFn: () => deleteJournalEntry(entryId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["journal"] });
      navigate("/journal");
    },
    onError: (error: ApiError) => reportError(error),
  });

  if (isLoading) {
    return <div className="p-6 text-sm text-text-secondary">Loading…</div>;
  }

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="p-6">
        <p className="text-sm text-text-secondary">
          This journal entry doesn&apos;t exist, or isn&apos;t yours.{" "}
          <Link to="/journal" className="text-accent">
            Back to Journal
          </Link>
        </p>
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="p-6">
        <p role="alert" className="text-sm text-danger">
          Couldn&apos;t load this journal entry.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <nav className="text-sm text-text-secondary">
        <Link to="/journal" className="text-accent">
          Journal
        </Link>
        {entry.trade_id && (
          <>
            {" "}
            /{" "}
            <Link to={`/trades/${entry.trade_id}`} className="text-accent">
              Trade
            </Link>
          </>
        )}
      </nav>

      <div className="rounded border border-border bg-bg-surface p-4">
        <p className="text-sm text-text-secondary">
          {entry.trade_id
            ? `Attached to trade #${entry.trade_id}`
            : `Period: ${entry.period_start} – ${entry.period_end}`}
        </p>
        <p className="mt-4 whitespace-pre-wrap text-sm text-text-primary">{entry.content}</p>
        <p className="mt-4 text-xs text-text-muted">
          Created {new Date(entry.created_at).toLocaleString()} · Updated{" "}
          {new Date(entry.updated_at).toLocaleString()}
        </p>
      </div>

      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => setEditOpen(true)}
          className="rounded border border-border px-3 py-2 text-sm text-text-primary"
        >
          Edit
        </button>
        <ConfirmDialog
          trigger={
            <button type="button" className="rounded border border-border px-3 py-2 text-sm text-danger">
              Delete
            </button>
          }
          title="Delete this journal entry?"
          description="This is a soft delete — the entry is removed from view but not permanently erased."
          confirmLabel="Delete"
          onConfirm={() => remove.mutate()}
          isConfirming={remove.isPending}
        />
      </div>

      <JournalEntryForm open={editOpen} onOpenChange={setEditOpen} mode={{ kind: "edit", entry }} />
    </div>
  );
}
