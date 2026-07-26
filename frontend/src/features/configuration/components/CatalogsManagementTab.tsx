import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { Badge } from "../../../components/Badge";
import { DataTable } from "../../../components/DataTable";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Select } from "../../../components/Select";
import {
  createCatalogEntry,
  deactivateCatalogEntry,
  listCatalogEntries,
  updateCatalogEntry,
} from "../catalogsApi";
import {
  CATALOG_KIND_OPTIONS,
  createCatalogEntrySchema,
  renameCatalogEntrySchema,
  type CreateCatalogEntryFormValues,
  type RenameCatalogEntryFormValues,
} from "../schemas";
import type { CatalogEntry } from "../types";

const KIND_FILTER_OPTIONS = [{ value: "", label: "All kinds" }, ...CATALOG_KIND_OPTIONS];

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §5.7 / §6.11: "One page, filtered by
 * kind... not five separate pages." No confirm dialog on deactivate — the
 * documented flow (§6.11) goes straight from "Deactivate" to the updated
 * list, unlike Publish, which explicitly asks for confirmation.
 */
export function CatalogsManagementTab() {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [kindFilter, setKindFilter] = useState<string>("");
  const [renamingId, setRenamingId] = useState<string | null>(null);

  const { data: entries, isLoading } = useQuery({
    queryKey: ["catalogs", kindFilter],
    queryFn: () => listCatalogEntries(kindFilter || undefined),
    staleTime: 60_000,
  });

  const {
    register: registerCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreateForm,
    control: createControl,
    formState: { errors: createErrors },
  } = useForm<CreateCatalogEntryFormValues>({
    resolver: zodResolver(createCatalogEntrySchema),
    defaultValues: { kind: undefined, name: "" },
  });

  const createEntry = useMutation({
    mutationFn: (values: CreateCatalogEntryFormValues) =>
      createCatalogEntry(values.kind, values.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["catalogs"] });
      resetCreateForm();
    },
    onError: (error: ApiError) => reportError(error),
  });

  const {
    register: registerRename,
    handleSubmit: handleRenameSubmit,
    reset: resetRenameForm,
  } = useForm<RenameCatalogEntryFormValues>({ resolver: zodResolver(renameCatalogEntrySchema) });

  const renameEntry = useMutation({
    mutationFn: (values: RenameCatalogEntryFormValues) =>
      updateCatalogEntry(renamingId as string, values.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["catalogs"] });
      setRenamingId(null);
      resetRenameForm();
    },
    onError: (error: ApiError) => reportError(error),
  });

  const deactivateEntry = useMutation({
    mutationFn: (id: string) => deactivateCatalogEntry(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["catalogs"] });
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <div>
      <h2 className="text-lg font-semibold text-text-primary">Catalogs Management</h2>

      <form
        onSubmit={handleCreateSubmit((values) => createEntry.mutate(values))}
        className="mt-4 flex flex-wrap items-end gap-3"
      >
        <div>
          <p className="mb-1 text-sm text-text-secondary">Kind</p>
          <Controller
            name="kind"
            control={createControl}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={CATALOG_KIND_OPTIONS}
                aria-label="New entry kind"
              />
            )}
          />
          {createErrors.kind && (
            <p className="mt-1 text-xs text-danger">{createErrors.kind.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="new-entry-name" className="mb-1 block text-sm text-text-secondary">
            Name
          </label>
          <input
            id="new-entry-name"
            className="w-56 rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...registerCreate("name")}
          />
          {createErrors.name && (
            <p className="mt-1 text-xs text-danger">{createErrors.name.message}</p>
          )}
        </div>
        <button
          type="submit"
          disabled={createEntry.isPending}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
        >
          {createEntry.isPending ? "Adding…" : "+ Add"}
        </button>
      </form>

      <div className="mt-6 max-w-xs">
        <p className="mb-1 text-sm text-text-secondary">Filter by kind</p>
        <Select
          value={kindFilter}
          onValueChange={setKindFilter}
          options={KIND_FILTER_OPTIONS}
          aria-label="Filter by kind"
        />
      </div>

      {isLoading || !entries ? (
        <div className="mt-6 text-sm text-text-secondary">Loading…</div>
      ) : entries.length === 0 ? (
        <p className="mt-6 text-sm text-text-secondary">
          No catalog entries for this filter yet — add one above.
        </p>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={[
              { key: "kind", header: "Kind", render: (e: CatalogEntry) => e.kind },
              {
                key: "name",
                header: "Name",
                render: (e: CatalogEntry) =>
                  renamingId === e.id ? (
                    <form
                      onSubmit={handleRenameSubmit((values) => renameEntry.mutate(values))}
                      className="flex items-center gap-2"
                    >
                      <input
                        defaultValue={e.name}
                        className="w-40 rounded border border-border bg-bg-base px-2 py-1 text-sm text-text-primary"
                        {...registerRename("name")}
                      />
                      <button type="submit" className="text-xs text-accent">
                        Save
                      </button>
                      <button
                        type="button"
                        onClick={() => setRenamingId(null)}
                        className="text-xs text-text-secondary"
                      >
                        Cancel
                      </button>
                    </form>
                  ) : (
                    e.name
                  ),
              },
              {
                key: "is_active",
                header: "Active",
                render: (e: CatalogEntry) => (
                  <Badge
                    label={e.is_active ? "Active" : "Inactive"}
                    tone={e.is_active ? "accent" : "muted"}
                  />
                ),
              },
              {
                key: "actions",
                header: "",
                render: (e: CatalogEntry) => (
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => {
                        setRenamingId(e.id);
                        resetRenameForm({ name: e.name });
                      }}
                      className="text-xs text-text-secondary hover:text-text-primary"
                    >
                      Rename
                    </button>
                    {e.is_active && (
                      <button
                        type="button"
                        onClick={() => deactivateEntry.mutate(e.id)}
                        disabled={deactivateEntry.isPending}
                        className="text-xs text-danger disabled:opacity-50"
                      >
                        Deactivate
                      </button>
                    )}
                  </div>
                ),
              },
            ]}
            rows={entries}
            getRowKey={(e) => e.id}
          />
        </div>
      )}
    </div>
  );
}
