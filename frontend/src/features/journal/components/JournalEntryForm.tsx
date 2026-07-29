import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { createJournalEntry, updateJournalEntry } from "../api";
import {
  journalContentSchema,
  periodJournalEntrySchema,
  type JournalContentFormValues,
  type PeriodJournalEntryFormValues,
} from "../schemas";
import type { JournalEntry } from "../types";

export type JournalEntryFormMode =
  | { kind: "create-trade-scoped"; tradeId: string }
  | { kind: "create-period-scoped" }
  | { kind: "edit"; entry: JournalEntry };

export interface JournalEntryFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: JournalEntryFormMode;
  onSaved?: (entry: JournalEntry) => void;
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.3's `JournalEntryForm` (Modal),
 * §6.10's two creation flows, and §5.7's Journal Entry Detail/Edit row:
 * "Reference type (Trade vs. period) is immutable after creation, per
 * the API — the UI must not offer to change it." Editing an existing
 * entry shows its reference as read-only context, never an editable
 * field; only `content` is ever submitted to `PATCH`.
 */
export function JournalEntryForm({ open, onOpenChange, mode, onSaved }: JournalEntryFormProps) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const isPeriodCreate = mode.kind === "create-period-scoped";

  const contentForm = useForm<JournalContentFormValues>({
    resolver: zodResolver(journalContentSchema),
    defaultValues: { content: mode.kind === "edit" ? mode.entry.content : "" },
  });
  const periodForm = useForm<PeriodJournalEntryFormValues>({
    resolver: zodResolver(periodJournalEntrySchema),
    defaultValues: { content: "", period_start: "", period_end: "" },
  });

  function handleSuccess(entry: JournalEntry) {
    queryClient.invalidateQueries({ queryKey: ["journal"] });
    contentForm.reset({ content: "" });
    periodForm.reset({ content: "", period_start: "", period_end: "" });
    onOpenChange(false);
    onSaved?.(entry);
  }

  const createTradeScoped = useMutation({
    mutationFn: (values: JournalContentFormValues) =>
      createJournalEntry({
        content: values.content,
        trade_id: mode.kind === "create-trade-scoped" ? mode.tradeId : undefined,
      }),
    onSuccess: handleSuccess,
    onError: (error: ApiError) => reportError(error),
  });

  const createPeriodScoped = useMutation({
    mutationFn: (values: PeriodJournalEntryFormValues) =>
      createJournalEntry({
        content: values.content,
        period_start: values.period_start,
        period_end: values.period_end,
      }),
    onSuccess: handleSuccess,
    onError: (error: ApiError) => reportError(error),
  });

  const update = useMutation({
    mutationFn: (values: JournalContentFormValues) => {
      if (mode.kind !== "edit") {
        throw new Error("update mutation used outside edit mode");
      }
      return updateJournalEntry(mode.entry.id, values);
    },
    onSuccess: handleSuccess,
    onError: (error: ApiError) => reportError(error),
  });

  const isPending = createTradeScoped.isPending || createPeriodScoped.isPending || update.isPending;

  const title =
    mode.kind === "edit"
      ? "Edit Journal Entry"
      : mode.kind === "create-trade-scoped"
        ? "New Journal Entry"
        : "New Journal Entry (Period)";

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title}>
      {mode.kind === "edit" && (
        <p className="mb-3 text-sm text-text-secondary">
          {mode.entry.trade_id
            ? `Attached to trade #${mode.entry.trade_id}`
            : `Period: ${mode.entry.period_start} – ${mode.entry.period_end}`}
          {" — the reference cannot be changed here."}
        </p>
      )}

      {isPeriodCreate ? (
        <form
          onSubmit={periodForm.handleSubmit((values) => createPeriodScoped.mutate(values))}
          className="flex flex-col gap-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="entry_period_start" className="mb-1 block text-sm text-text-secondary">
                Period Start
              </label>
              <input
                id="entry_period_start"
                type="date"
                className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
                {...periodForm.register("period_start")}
              />
              {periodForm.formState.errors.period_start && (
                <p className="mt-1 text-xs text-danger">
                  {periodForm.formState.errors.period_start.message}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="entry_period_end" className="mb-1 block text-sm text-text-secondary">
                Period End
              </label>
              <input
                id="entry_period_end"
                type="date"
                className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
                {...periodForm.register("period_end")}
              />
              {periodForm.formState.errors.period_end && (
                <p className="mt-1 text-xs text-danger">
                  {periodForm.formState.errors.period_end.message}
                </p>
              )}
            </div>
          </div>
          <div>
            <label htmlFor="period_content" className="mb-1 block text-sm text-text-secondary">
              Content
            </label>
            <textarea
              id="period_content"
              rows={6}
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...periodForm.register("content")}
            />
            {periodForm.formState.errors.content && (
              <p className="mt-1 text-xs text-danger">
                {periodForm.formState.errors.content.message}
              </p>
            )}
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
              disabled={isPending}
              className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
            >
              {isPending ? "Saving…" : "Save Entry"}
            </button>
          </div>
        </form>
      ) : (
        <form
          onSubmit={contentForm.handleSubmit((values) =>
            mode.kind === "edit" ? update.mutate(values) : createTradeScoped.mutate(values),
          )}
          className="flex flex-col gap-4"
        >
          <div>
            <label htmlFor="content" className="mb-1 block text-sm text-text-secondary">
              Content
            </label>
            <textarea
              id="content"
              rows={6}
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...contentForm.register("content")}
            />
            {contentForm.formState.errors.content && (
              <p className="mt-1 text-xs text-danger">
                {contentForm.formState.errors.content.message}
              </p>
            )}
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
              disabled={isPending}
              className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
            >
              {isPending ? "Saving…" : "Save Entry"}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
