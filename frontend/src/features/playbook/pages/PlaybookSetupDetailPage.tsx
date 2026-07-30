import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../../../api/errors";
import { Badge } from "../../../components/Badge";
import { ConfirmDialog } from "../../../components/ConfirmDialog";
import { useErrorReporter } from "../../../components/ErrorContext";
import { deprecatePlaybookSetup, getPlaybookSetup } from "../api";
import { AttachmentsCard } from "../components/AttachmentsCard";
import { EditPlaybookSetupModal } from "../components/EditPlaybookSetupModal";
import { PerformanceCard } from "../components/PerformanceCard";
import { playbookKeys } from "../queryKeys";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's "Playbook Setup Detail" row:
 * "Setup definition + live performance... Performance numbers are never
 * edited here — read-only, sourced live." Deprecate
 * (`POST /playbook-setups/{id}/deprecate`, not named in the Frontend
 * Blueprint but resolved by precedent, Sprint 7.2 pre-analysis) reuses
 * `ConfirmDialog` exactly the way its own docstring already anticipates
 * ("Publish... given irreversibility") — Domain Model §13.4's lifecycle
 * has no reverse transition from `Deprecated`.
 */
export function PlaybookSetupDetailPage() {
  const { setupId } = useParams<{ setupId: string }>();
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [editOpen, setEditOpen] = useState(false);

  const {
    data: setup,
    isLoading,
    error,
  } = useQuery({
    queryKey: playbookKeys.detail(setupId as string),
    queryFn: () => getPlaybookSetup(setupId as string),
    enabled: setupId !== undefined,
    retry: false,
  });

  const deprecate = useMutation({
    mutationFn: () => deprecatePlaybookSetup(setupId as string),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: playbookKeys.detail(setupId as string) });
      queryClient.invalidateQueries({ queryKey: playbookKeys.list() });
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
          This setup doesn&apos;t exist.{" "}
          <Link to="/playbook" className="text-accent">
            Back to Playbook
          </Link>
        </p>
      </div>
    );
  }

  if (error || !setup) {
    return (
      <div className="p-6">
        <p role="alert" className="text-sm text-danger">
          Couldn&apos;t load this setup.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <nav className="text-sm text-text-secondary">
        <Link to="/playbook" className="text-accent">
          Playbook
        </Link>{" "}
        / {setup.name}
      </nav>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-text-primary">{setup.name}</h1>
          <Badge
            label={setup.status === "active" ? "Active" : "Deprecated"}
            tone={setup.status === "active" ? "accent" : "muted"}
          />
        </div>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setEditOpen(true)}
            className="rounded border border-border px-3 py-2 text-sm text-text-primary"
          >
            Edit
          </button>
          {setup.status === "active" && (
            <ConfirmDialog
              trigger={
                <button
                  type="button"
                  className="rounded border border-border px-3 py-2 text-sm text-text-primary"
                >
                  Deprecate
                </button>
              }
              title="Deprecate this Setup?"
              description="It stays retained for historical attribution and is no longer offered for new Trades. This cannot be undone."
              confirmLabel="Deprecate"
              onConfirm={() => deprecate.mutate()}
              isConfirming={deprecate.isPending}
            />
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 rounded border border-border bg-bg-surface p-4 sm:grid-cols-2">
        <div>
          <p className="text-sm text-text-secondary">Entry Criteria</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">
            {setup.entry_criteria || "—"}
          </p>
        </div>
        <div>
          <p className="text-sm text-text-secondary">Exit Criteria</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">
            {setup.exit_criteria || "—"}
          </p>
        </div>
        <div>
          <p className="text-sm text-text-secondary">Ideal Conditions</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">
            {setup.ideal_conditions || "—"}
          </p>
        </div>
        <div>
          <p className="text-sm text-text-secondary">Risk Rules</p>
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">
            {setup.risk_rules || "—"}
          </p>
        </div>
      </div>

      <PerformanceCard performance={setup.performance} />

      <AttachmentsCard setupId={setup.id} attachments={setup.attachments} />

      <EditPlaybookSetupModal setup={setup} open={editOpen} onOpenChange={setEditOpen} />
    </div>
  );
}
