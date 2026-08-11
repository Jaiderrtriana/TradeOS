import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { FormProvider } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Tabs } from "../../../components/Tabs";
import { dateOnlyToAwareIso, usePreferencesTimezone } from "../../../shared/timezone";
import { registerTrade } from "../api";
import { useTradeEntryForm } from "../hooks/useTradeEntryForm";
import { tradingKeys } from "../queryKeys";
import type { RegisterTradePayload } from "../types";
import { ProForm } from "./ProForm";
import { SimpleForm } from "./SimpleForm";
import { TradeTypeDialog } from "./TradeTypeDialog";

export interface TradeEntryModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (tradeId: string) => void;
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.2's `NewTradeModal` — Tabs (Simple /
 * Pro, Principle 7), each a Form sharing one `useTradeEntryForm` instance.
 * Simple is the default tab (Sprint 4.4 resolution of Product Bible Open
 * Question 4 / Master Plan OQ-2 — see CHANGELOG.md); Pro remains
 * first-class but secondary. §6.2: `POST /trades` is synchronous, so
 * there is no intermediate "processing" screen — on success this modal
 * simply closes and the caller navigates straight to Trade Detail,
 * which already shows the computed Evaluation (or, for a `Planned`
 * Trade, the "no Evaluation yet" state — `EvaluationSummaryCard`).
 *
 * v2.0 (Trade Entry redesign): submission intercepts before RHF's own
 * validation whenever `status != planned` and `scoring_profile` is still
 * empty, opening `TradeTypeDialog` instead of surfacing an inline
 * required-field error (the approved "Option 4" just-in-time prompt —
 * see that component's own docstring). Picking a Trade Type there sets
 * the field and immediately re-submits; every other validation failure
 * still surfaces inline exactly as before.
 */
export function TradeEntryModal({ open, onOpenChange, onCreated }: TradeEntryModalProps) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const timezone = usePreferencesTimezone();
  const { form, mode, setMode, checklistAnswers, handleAnswerChange, reset } = useTradeEntryForm();
  const [tradeTypeDialogOpen, setTradeTypeDialogOpen] = useState(false);

  const createTrade = useMutation({
    mutationFn: (payload: RegisterTradePayload) => registerTrade(payload),
    onSuccess: (trade) => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      reset();
      onOpenChange(false);
      onCreated(trade.id);
    },
    onError: (error: ApiError) => reportError(error),
  });

  function handleClose(nextOpen: boolean) {
    if (!nextOpen) {
      reset();
      setTradeTypeDialogOpen(false);
    }
    onOpenChange(nextOpen);
  }

  function onSubmit(values: RegisterTradePayload) {
    // `entered_at`/`closed_at` are date-only strings ("2026-01-01") from
    // Simple/Pro's shared `<input type="date">` fields — anchored to the
    // resolved timezone before they ever reach the API, never left for
    // the backend to guess (Sprint 4 Fase 2, OQ-7 contract). Applied once
    // here rather than in each form, since both modes submit through
    // this one handler.
    const payload: RegisterTradePayload = {
      ...values,
      entered_at: dateOnlyToAwareIso(values.entered_at, timezone),
      closed_at: dateOnlyToAwareIso(values.closed_at, timezone),
      checklist_answers: Object.keys(checklistAnswers).length > 0 ? checklistAnswers : undefined,
    };
    createTrade.mutate(payload);
  }

  function handleFormSubmit(event: FormEvent<HTMLFormElement>) {
    const values = form.getValues();
    if (values.status !== "planned" && !values.scoring_profile) {
      event.preventDefault();
      setTradeTypeDialogOpen(true);
      return;
    }
    void form.handleSubmit(onSubmit)(event);
  }

  function handleTradeTypeSelected(profileCode: string) {
    form.setValue("scoring_profile", profileCode, { shouldValidate: false });
    setTradeTypeDialogOpen(false);
    void form.handleSubmit(onSubmit)();
  }

  return (
    <Modal open={open} onOpenChange={handleClose} title="New Trade">
      <FormProvider {...form}>
        <form onSubmit={handleFormSubmit}>
          <Tabs
            value={mode}
            onValueChange={(value) => setMode(value as "simple" | "pro")}
            defaultValue="simple"
            items={[
              { value: "simple", label: "Simple (predeterminado)", content: <SimpleForm /> },
              {
                value: "pro",
                label: "Cambiar a Pro",
                content: (
                  <ProForm
                    checklistAnswers={checklistAnswers}
                    onAnswerChange={handleAnswerChange}
                  />
                ),
              },
            ]}
          />

          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => handleClose(false)}
              className="rounded border border-border px-3 py-2 text-sm text-text-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createTrade.isPending}
              className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
            >
              {createTrade.isPending ? "Saving…" : "Save Trade"}
            </button>
          </div>
        </form>
      </FormProvider>

      <TradeTypeDialog
        open={tradeTypeDialogOpen}
        onOpenChange={setTradeTypeDialogOpen}
        onSelect={handleTradeTypeSelected}
      />
    </Modal>
  );
}
