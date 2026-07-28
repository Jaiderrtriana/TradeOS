import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { upsertChecklistAnswer, type ChecklistAnswers } from "../../../shared/checklist";
import { tradeEntrySchema, type TradeEntryFormInput, type TradeEntryFormValues } from "../schemas";

export type TradeEntryMode = "simple" | "pro";

/**
 * Owns the one `useForm` instance shared by `SimpleForm`/`ProForm` (via
 * `FormProvider`/`useFormContext`) so toggling Simple ↔ Pro
 * (`TRADEOS_FRONTEND_BLUEPRINT.md` §5.7: "Simple (predeterminado)" /
 * "Cambiar a Pro") never loses already-entered values — plus the
 * `checklist_answers` state, which isn't a plain registered field (a
 * dynamic per-criterion map, same pattern `EvaluationPreviewForm`
 * established, Sprint 3.3).
 */
export function useTradeEntryForm() {
  const [mode, setMode] = useState<TradeEntryMode>("simple");
  const [checklistAnswers, setChecklistAnswers] = useState<ChecklistAnswers>({});

  const form = useForm<TradeEntryFormInput, unknown, TradeEntryFormValues>({
    resolver: zodResolver(tradeEntrySchema),
    defaultValues: {
      market: "",
      direction: undefined,
      entry_price: undefined,
      stop_loss: undefined,
      scoring_profile: "",
    },
  });

  function handleAnswerChange(sourceField: string, value: string | number | undefined) {
    setChecklistAnswers((previous) => upsertChecklistAnswer(previous, sourceField, value));
  }

  function reset() {
    form.reset();
    setChecklistAnswers({});
    setMode("simple");
  }

  return { form, mode, setMode, checklistAnswers, handleAnswerChange, reset };
}
