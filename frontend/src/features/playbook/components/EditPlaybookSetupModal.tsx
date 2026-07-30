import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import type { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { updatePlaybookSetup } from "../api";
import { playbookKeys } from "../queryKeys";
import { updatePlaybookSetupSchema, type UpdatePlaybookSetupFormValues } from "../schemas";
import type { PlaybookSetupDetail } from "../types";

/**
 * `PATCH /playbook-setups/{id}` — genuinely partial server-side (an
 * omitted field stays unchanged), but this form always pre-fills every
 * field with the setup's *current* value and always submits all four
 * together (`types.ts`'s `UpdatePlaybookSetupPayload` docstring) — the
 * same "resend the full current-or-edited state" discipline
 * `AmendTradeModal` already applies to Trade, so a field the trader
 * never touches can never be silently lost or overwritten with
 * something wrong (Sprint 7.2 pre-analysis: this is the exact concern
 * flagged for special attention).
 */
export function EditPlaybookSetupModal({
  setup,
  open,
  onOpenChange,
}: {
  setup: PlaybookSetupDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const { register, handleSubmit } = useForm<UpdatePlaybookSetupFormValues>({
    resolver: zodResolver(updatePlaybookSetupSchema),
    // `values` (not `defaultValues`) keeps the form synced to the
    // setup's real current state every time it changes -- including
    // right after a save, so re-opening the modal never shows stale data.
    values: {
      entry_criteria: setup.entry_criteria,
      exit_criteria: setup.exit_criteria,
      ideal_conditions: setup.ideal_conditions,
      risk_rules: setup.risk_rules,
    },
  });

  const update = useMutation({
    mutationFn: (values: UpdatePlaybookSetupFormValues) => updatePlaybookSetup(setup.id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: playbookKeys.detail(setup.id) });
      queryClient.invalidateQueries({ queryKey: playbookKeys.list() });
      onOpenChange(false);
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Edit Setup Documentation">
      <form
        onSubmit={handleSubmit((values) => update.mutate(values))}
        className="flex flex-col gap-4"
      >
        <div>
          <label htmlFor="entry_criteria" className="mb-1 block text-sm text-text-secondary">
            Entry Criteria
          </label>
          <textarea
            id="entry_criteria"
            rows={3}
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("entry_criteria")}
          />
        </div>

        <div>
          <label htmlFor="exit_criteria" className="mb-1 block text-sm text-text-secondary">
            Exit Criteria
          </label>
          <textarea
            id="exit_criteria"
            rows={3}
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("exit_criteria")}
          />
        </div>

        <div>
          <label htmlFor="ideal_conditions" className="mb-1 block text-sm text-text-secondary">
            Ideal Conditions
          </label>
          <textarea
            id="ideal_conditions"
            rows={3}
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("ideal_conditions")}
          />
        </div>

        <div>
          <label htmlFor="risk_rules" className="mb-1 block text-sm text-text-secondary">
            Risk Rules
          </label>
          <textarea
            id="risk_rules"
            rows={3}
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("risk_rules")}
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded border border-border px-3 py-2 text-sm text-text-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={update.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {update.isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
