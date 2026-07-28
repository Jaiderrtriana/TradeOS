import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FormProvider } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Tabs } from "../../../components/Tabs";
import { registerTrade } from "../api";
import { useTradeEntryForm } from "../hooks/useTradeEntryForm";
import { tradingKeys } from "../queryKeys";
import type { RegisterTradePayload } from "../types";
import { ProForm } from "./ProForm";
import { SimpleForm } from "./SimpleForm";

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
 * which already shows the computed Evaluation.
 */
export function TradeEntryModal({ open, onOpenChange, onCreated }: TradeEntryModalProps) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const { form, mode, setMode, checklistAnswers, handleAnswerChange, reset } = useTradeEntryForm();

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
    }
    onOpenChange(nextOpen);
  }

  function onSubmit(values: RegisterTradePayload) {
    const payload: RegisterTradePayload = {
      ...values,
      checklist_answers: Object.keys(checklistAnswers).length > 0 ? checklistAnswers : undefined,
    };
    createTrade.mutate(payload);
  }

  return (
    <Modal open={open} onOpenChange={handleClose} title="New Trade">
      <FormProvider {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
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
                  <ProForm checklistAnswers={checklistAnswers} onAnswerChange={handleAnswerChange} />
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
    </Modal>
  );
}
