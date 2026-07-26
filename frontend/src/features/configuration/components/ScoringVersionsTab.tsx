import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Badge } from "../../../components/Badge";
import { ConfirmDialog } from "../../../components/ConfirmDialog";
import { DataTable } from "../../../components/DataTable";
import { Select } from "../../../components/Select";
import { useErrorReporter } from "../../../components/ErrorContext";
import { ApiError } from "../../../api/errors";
import {
  createDraftConfigurationVersion,
  listConfigurationVersions,
  listConfigurationWeights,
  listScoringCriteria,
  listScoringProfiles,
  publishConfigurationVersion,
  updateDraftWeight,
} from "../api";
import {
  createDraftVersionSchema,
  weightFormSchema,
  type CreateDraftVersionFormValues,
  type WeightFormInput,
  type WeightFormValues,
} from "../schemas";
import type {
  ScoringConfigurationVersion,
  ScoringConfigurationVersionStatus,
  ScoringCriterion,
  ScoringProfile,
  ScoringWeight,
} from "../types";

const STATUS_TONE: Record<ScoringConfigurationVersionStatus, "accent" | "neutral" | "muted"> = {
  draft: "neutral",
  published: "accent",
  superseded: "muted",
};

/**
 * TRADEOS_FRONTEND_BLUEPRINT.md §5.5 / §8.5 — approved scope (Sprint
 * 2.3): view versions, view criteria/weights as reference, create a
 * draft, edit a draft's weights, publish. Creating/editing
 * ScoringCriterion definitions is explicitly out of scope — criteria are
 * read-only here (`GET /configuration/scoring-criteria`).
 *
 * Version detail is an inline expansion under the selected row, not a
 * Drawer or a nested route (approved decision) — keeps the whole page on
 * one URL, `/configuration`.
 */
export function ScoringVersionsTab() {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const { data: versions, isLoading: versionsLoading } = useQuery({
    queryKey: ["configuration", "versions"],
    queryFn: listConfigurationVersions,
    staleTime: 60_000,
  });

  const { data: criteria } = useQuery({
    queryKey: ["configuration", "criteria"],
    queryFn: listScoringCriteria,
    staleTime: 60_000,
  });

  const { data: profiles } = useQuery({
    queryKey: ["configuration", "profiles"],
    queryFn: listScoringProfiles,
    staleTime: 60_000,
  });

  const { data: weights } = useQuery({
    queryKey: ["configuration", "versions", selectedVersionId, "weights"],
    queryFn: () => listConfigurationWeights(selectedVersionId as string),
    enabled: selectedVersionId !== null,
    staleTime: 60_000,
  });

  const {
    register: registerDraft,
    handleSubmit: handleDraftSubmit,
    reset: resetDraftForm,
    formState: { errors: draftErrors },
  } = useForm<CreateDraftVersionFormValues>({ resolver: zodResolver(createDraftVersionSchema) });

  const createDraft = useMutation({
    mutationFn: (values: CreateDraftVersionFormValues) =>
      createDraftConfigurationVersion(values.version_label),
    onSuccess: (version) => {
      queryClient.invalidateQueries({ queryKey: ["configuration", "versions"] });
      setSelectedVersionId(version.id);
      resetDraftForm();
    },
    onError: (error: ApiError) => reportError(error),
  });

  const publish = useMutation({
    mutationFn: (versionId: string) => publishConfigurationVersion(versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["configuration", "versions"] });
    },
    onError: (error: ApiError) => reportError(error),
  });

  const selectedVersion = versions?.find((v) => v.id === selectedVersionId) ?? null;
  const isDraft = selectedVersion?.status === "draft";

  if (versionsLoading || !versions) {
    return <div className="p-6 text-sm text-text-secondary">Loading…</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Scoring Configuration</h2>
      </div>

      <form
        onSubmit={handleDraftSubmit((values) => createDraft.mutate(values))}
        className="mt-4 flex items-end gap-3"
      >
        <div>
          <label htmlFor="version_label" className="block text-sm text-text-secondary">
            New draft label
          </label>
          <input
            id="version_label"
            className="mt-1 w-48 rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            placeholder="v1.1"
            {...registerDraft("version_label")}
          />
          {draftErrors.version_label && (
            <p className="mt-1 text-xs text-danger">{draftErrors.version_label.message}</p>
          )}
        </div>
        <button
          type="submit"
          disabled={createDraft.isPending}
          className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
        >
          {createDraft.isPending ? "Creating…" : "+ New Draft"}
        </button>
      </form>

      {versions.length === 0 ? (
        <p className="mt-6 text-sm text-text-secondary">
          No configuration versions yet — create the first draft above.
        </p>
      ) : (
        <div className="mt-6">
          <DataTable
            columns={[
              { key: "version_label", header: "Version", render: (v) => v.version_label },
              {
                key: "status",
                header: "Status",
                render: (v) => <Badge label={v.status} tone={STATUS_TONE[v.status]} />,
              },
              {
                key: "published_at",
                header: "Published",
                render: (v) => (v.published_at ? new Date(v.published_at).toLocaleString() : "—"),
              },
            ]}
            rows={versions}
            getRowKey={(v) => v.id}
            onRowClick={(v) => setSelectedVersionId(v.id === selectedVersionId ? null : v.id)}
            isRowSelected={(v) => v.id === selectedVersionId}
          />
        </div>
      )}

      {selectedVersion && (
        <VersionDetail
          version={selectedVersion}
          weights={weights ?? []}
          criteria={criteria ?? []}
          profiles={profiles ?? []}
          isDraft={isDraft}
          onPublish={() => publish.mutate(selectedVersion.id)}
          isPublishing={publish.isPending}
        />
      )}
    </div>
  );
}

interface VersionDetailProps {
  version: ScoringConfigurationVersion;
  weights: ScoringWeight[];
  criteria: ScoringCriterion[];
  profiles: ScoringProfile[];
  isDraft: boolean;
  onPublish: () => void;
  isPublishing: boolean;
}

function VersionDetail({
  version,
  weights,
  criteria,
  profiles,
  isDraft,
  onPublish,
  isPublishing,
}: VersionDetailProps) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const criterionById = new Map(criteria.map((c) => [c.id, c]));
  const profileByCode = new Map(profiles.map((p) => [p.code, p]));

  const {
    register: registerWeight,
    handleSubmit: handleWeightSubmit,
    reset: resetWeightForm,
    control: weightControl,
    formState: { errors: weightErrors },
  } = useForm<WeightFormInput, unknown, WeightFormValues>({
    resolver: zodResolver(weightFormSchema),
    defaultValues: { criterion_id: "", profile_code: "", weight: 0 },
  });

  const upsertWeight = useMutation({
    mutationFn: (values: WeightFormValues) => updateDraftWeight(version.id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["configuration", "versions", version.id, "weights"],
      });
      resetWeightForm();
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <div className="mt-4 rounded border border-border bg-bg-surface p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">
          {version.version_label} — criteria &amp; weights
        </h3>
        {isDraft && (
          <ConfirmDialog
            trigger={
              <button
                type="button"
                className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary"
              >
                Publish
              </button>
            }
            title="Publish this version?"
            description="Publishing supersedes the currently published version. This does not re-evaluate any existing trades — that remains a separate, per-trade action."
            confirmLabel="Publish"
            onConfirm={onPublish}
            isConfirming={isPublishing}
          />
        )}
      </div>

      {weights.length === 0 ? (
        <p className="mt-3 text-sm text-text-secondary">No weights added to this version yet.</p>
      ) : (
        <div className="mt-3">
          <DataTable
            columns={[
              {
                key: "criterion",
                header: "Criterion",
                render: (w) => criterionById.get(w.criterion_id)?.name ?? w.criterion_id,
              },
              {
                key: "engine",
                header: "Engine",
                render: (w) => criterionById.get(w.criterion_id)?.engine_type_code ?? "—",
              },
              {
                key: "profile",
                header: "Profile",
                render: (w) => profileByCode.get(w.profile_code)?.display_name ?? w.profile_code,
              },
              { key: "weight", header: "Weight", render: (w) => w.weight },
              {
                key: "active",
                header: "Active",
                render: (w) => (w.is_active ? "Yes" : "No"),
              },
            ]}
            rows={weights}
            getRowKey={(w) => w.id}
          />
        </div>
      )}

      {/* §5.5: editing weights is "blocked entirely (not just validated) if
          the version isn't a draft" — the form itself doesn't render. */}
      {isDraft && (
        <form
          onSubmit={handleWeightSubmit((values) => upsertWeight.mutate(values))}
          className="mt-4 flex flex-wrap items-end gap-3"
        >
          <div>
            <p className="mb-1 text-sm text-text-secondary">Criterion</p>
            <Controller
              name="criterion_id"
              control={weightControl}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  options={criteria.map((c) => ({
                    value: c.id,
                    label: `${c.name} (${c.engine_type_code})`,
                  }))}
                  aria-label="Criterion"
                />
              )}
            />
            {weightErrors.criterion_id && (
              <p className="mt-1 text-xs text-danger">{weightErrors.criterion_id.message}</p>
            )}
          </div>
          <div>
            <p className="mb-1 text-sm text-text-secondary">Profile</p>
            <Controller
              name="profile_code"
              control={weightControl}
              render={({ field }) => (
                <Select
                  value={field.value}
                  onValueChange={field.onChange}
                  options={profiles.map((p) => ({ value: p.code, label: p.display_name }))}
                  aria-label="Profile"
                />
              )}
            />
            {weightErrors.profile_code && (
              <p className="mt-1 text-xs text-danger">{weightErrors.profile_code.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="weight" className="mb-1 block text-sm text-text-secondary">
              Weight
            </label>
            <input
              id="weight"
              type="number"
              step="any"
              className="w-28 rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...registerWeight("weight")}
            />
            {weightErrors.weight && (
              <p className="mt-1 text-xs text-danger">{weightErrors.weight.message}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={upsertWeight.isPending}
            className="rounded border border-border px-3 py-2 text-sm text-text-primary disabled:opacity-50"
          >
            {upsertWeight.isPending ? "Saving…" : "Add / Update Weight"}
          </button>
        </form>
      )}
    </div>
  );
}
