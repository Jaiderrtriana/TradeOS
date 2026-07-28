import { useQuery } from "@tanstack/react-query";
import { Controller, useFormContext } from "react-hook-form";

import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { catalogEntryKeys, listCatalogEntries } from "../../../shared/catalogEntries";
import type { ChecklistAnswers } from "../../../shared/checklist";
import type { TradeEntryFormInput, TradeEntryFormValues } from "../schemas";
import { ChecklistSection } from "./ChecklistSection";
import { SimpleForm } from "./SimpleForm";
import { TradeEntryScorePreview } from "./TradeEntryScorePreview";

const RESULT_OPTIONS = [
  { value: "open", label: "Open" },
  { value: "tp", label: "Take Profit" },
  { value: "sl", label: "Stop Loss" },
  { value: "be", label: "Break Even" },
];

export interface ProFormProps {
  checklistAnswers: ChecklistAnswers;
  onAnswerChange: (sourceField: string, value: string | number | undefined) => void;
}

function useCatalogOptions(kind: string) {
  const { data } = useQuery({
    queryKey: catalogEntryKeys.list(kind),
    queryFn: () => listCatalogEntries(kind),
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });
  return (data ?? []).filter((entry) => entry.is_active).map((entry) => ({
    value: entry.id,
    label: entry.name,
  }));
}

/**
 * Pro Trade Entry — `TRADEOS_FRONTEND_BLUEPRINT.md` Principle 7: "a 'Pro'
 * path that surfaces everything the API accepts, never only the maximal
 * form." Builds on `SimpleForm`'s required fields (same shared form
 * context, `TRADEOS_FRONTEND_BLUEPRINT.md` §8.2's component tree) and
 * adds every optional `POST /trades` field plus the live-scored
 * checklist (§6.3).
 */
export function ProForm({ checklistAnswers, onAnswerChange }: ProFormProps) {
  const {
    register,
    control,
    watch,
    formState: { errors },
  } = useFormContext<TradeEntryFormInput, unknown, TradeEntryFormValues>();

  const strategyOptions = useCatalogOptions("strategy");
  const setupOptions = useCatalogOptions("setup");
  const sessionOptions = useCatalogOptions("session");
  const entryTriggerOptions = useCatalogOptions("entry_trigger");
  const scoringProfile = watch("scoring_profile");

  return (
    <div className="flex flex-col gap-6">
      <SimpleForm />

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="exit_price" className="mb-1 block text-sm text-text-secondary">
            Exit Price
          </label>
          <input
            id="exit_price"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("exit_price")}
          />
        </div>
        <div>
          <p className="mb-1 text-sm text-text-secondary">Result</p>
          <Controller
            name="result"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? "open"}
                onValueChange={field.onChange}
                options={RESULT_OPTIONS}
                aria-label="Result"
              />
            )}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="size" className="mb-1 block text-sm text-text-secondary">
            Size
          </label>
          <input
            id="size"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("size")}
          />
          {errors.size && <p className="mt-1 text-xs text-danger">{errors.size.message}</p>}
        </div>
        <div>
          <label htmlFor="leverage" className="mb-1 block text-sm text-text-secondary">
            Leverage
          </label>
          <input
            id="leverage"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("leverage")}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="mfe_price" className="mb-1 block text-sm text-text-secondary">
            MFE Price
          </label>
          <input
            id="mfe_price"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("mfe_price")}
          />
        </div>
        <div>
          <label htmlFor="mae_price" className="mb-1 block text-sm text-text-secondary">
            MAE Price
          </label>
          <input
            id="mae_price"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("mae_price")}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="mb-1 text-sm text-text-secondary">Strategy</p>
          <Controller
            name="strategy_id"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={[{ value: "", label: "—" }, ...strategyOptions]}
                aria-label="Strategy"
              />
            )}
          />
        </div>
        <div>
          <p className="mb-1 text-sm text-text-secondary">Setup</p>
          <Controller
            name="setup_id"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={[{ value: "", label: "—" }, ...setupOptions]}
                aria-label="Setup"
              />
            )}
          />
        </div>
        <div>
          <p className="mb-1 text-sm text-text-secondary">Session</p>
          <Controller
            name="session_id"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={[{ value: "", label: "—" }, ...sessionOptions]}
                aria-label="Session"
              />
            )}
          />
        </div>
        <div>
          <p className="mb-1 text-sm text-text-secondary">Entry Trigger</p>
          <Controller
            name="entry_trigger_id"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={[{ value: "", label: "—" }, ...entryTriggerOptions]}
                aria-label="Entry Trigger"
              />
            )}
          />
        </div>
      </div>

      <div>
        <label htmlFor="notes" className="mb-1 block text-sm text-text-secondary">
          Notes
        </label>
        <textarea
          id="notes"
          rows={3}
          className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
          {...register("notes")}
        />
      </div>

      <ChecklistSection answers={checklistAnswers} onAnswerChange={onAnswerChange} />

      <TradeEntryScorePreview scoringProfile={scoringProfile ?? ""} checklistAnswers={checklistAnswers} />
    </div>
  );
}
