import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { ApiError } from "../../../api/errors";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import { useErrorReporter } from "../../../components/ErrorContext";
import { CatalogPickerModal } from "../../trading/components/CatalogPickerModal";
import { createPlaybookSetup, listPlaybookSetups } from "../api";
import { playbookKeys } from "../queryKeys";
import type { PlaybookSetupSummary } from "../types";

const SETUP_KIND = "setup";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §5.7's "Playbook List" row: "Browse
 * Setups... Empty state: 'No setups documented yet.'" Creation
 * (`POST /playbook-setups`, not separately named in the Master Plan
 * bullet or in this row's own "Key API Dependency" column) is resolved
 * by direct precedent from Journal List's identical shape (Sprint 5.1):
 * a "+ New" action reusing the already-built, kind-generic
 * `CatalogPickerModal` (`features/trading/components/`, its own
 * docstring already anticipating exactly this reuse) — picking a
 * `kind=setup` Catalog entry is the entire creation flow; the four text
 * fields are documented afterward via Edit on the new Setup's own
 * Detail page (Sprint 7.2 pre-analysis).
 */
export function PlaybookListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [pickerOpen, setPickerOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: playbookKeys.list(),
    queryFn: () => listPlaybookSetups(),
  });

  const setups = data?.data ?? [];

  const create = useMutation({
    mutationFn: (catalogEntryId: string) =>
      createPlaybookSetup({ catalog_entry_id: catalogEntryId }),
    onSuccess: (setup) => {
      queryClient.invalidateQueries({ queryKey: playbookKeys.list() });
      setPickerOpen(false);
      navigate(`/playbook/${setup.id}`);
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-text-primary">Playbook</h1>
        <button
          type="button"
          onClick={() => setPickerOpen(true)}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary"
        >
          + New Setup
        </button>
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="text-sm text-text-secondary">Loading…</div>
        ) : setups.length === 0 ? (
          <p className="text-sm text-text-secondary">
            No setups documented yet — use “+ New Setup” to link your first one.
          </p>
        ) : (
          <DataTable<PlaybookSetupSummary>
            columns={[
              { key: "name", header: "Name", render: (setup) => setup.name },
              {
                key: "status",
                header: "Status",
                render: (setup) => (
                  <Badge
                    label={setup.status === "active" ? "Active" : "Deprecated"}
                    tone={setup.status === "active" ? "accent" : "muted"}
                  />
                ),
              },
              {
                key: "updated_at",
                header: "Last Updated",
                render: (setup) => new Date(setup.updated_at).toLocaleString(),
              },
            ]}
            rows={setups}
            getRowKey={(setup) => setup.id}
            onRowClick={(setup) => navigate(`/playbook/${setup.id}`)}
          />
        )}
      </div>

      <CatalogPickerModal
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        kind={SETUP_KIND}
        title="Link a Setup"
        excludeIds={setups.map((setup) => setup.catalog_entry_id)}
        onSelect={(catalogEntryId) => create.mutate(catalogEntryId)}
        isSelecting={create.isPending}
      />
    </div>
  );
}
