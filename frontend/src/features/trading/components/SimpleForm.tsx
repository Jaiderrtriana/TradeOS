import { useQuery } from "@tanstack/react-query";
import { Controller, useFormContext } from "react-hook-form";

import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { listScoringProfiles, scoringReferenceKeys } from "../../../shared/scoringReferenceData";
import type { TradeEntryFormInput, TradeEntryFormValues } from "../schemas";

const DIRECTION_OPTIONS = [
  { value: "long", label: "Long" },
  { value: "short", label: "Short" },
];

/**
 * Simple Trade Entry — `TRADEOS_FRONTEND_BLUEPRINT.md` Principle 7: "a
 * 'Simple' path that asks for only the required fields." Exactly the
 * required subset of `POST /trades` (`market`, `direction`, `entry_price`,
 * `stop_loss`, `scoring_profile`) — nothing else. Reads the shared
 * `useTradeEntryForm` context via `useFormContext`, so switching to Pro
 * mode never loses what was typed here.
 */
export function SimpleForm() {
  const {
    register,
    control,
    formState: { errors },
  } = useFormContext<TradeEntryFormInput, unknown, TradeEntryFormValues>();

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <label htmlFor="market" className="mb-1 block text-sm text-text-secondary">
          Market
        </label>
        <input
          id="market"
          className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
          {...register("market")}
        />
        {errors.market && <p className="mt-1 text-xs text-danger">{errors.market.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="mb-1 text-sm text-text-secondary">Direction</p>
          <Controller
            name="direction"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={field.onChange}
                options={DIRECTION_OPTIONS}
                aria-label="Direction"
              />
            )}
          />
          {errors.direction && (
            <p className="mt-1 text-xs text-danger">{errors.direction.message}</p>
          )}
        </div>
        <div>
          <p className="mb-1 text-sm text-text-secondary">Scoring Profile</p>
          <Controller
            name="scoring_profile"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value}
                onValueChange={field.onChange}
                options={(profiles ?? []).map((p) => ({ value: p.code, label: p.display_name }))}
                aria-label="Scoring Profile"
              />
            )}
          />
          {errors.scoring_profile && (
            <p className="mt-1 text-xs text-danger">{errors.scoring_profile.message}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="entry_price" className="mb-1 block text-sm text-text-secondary">
            Entry Price
          </label>
          <input
            id="entry_price"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("entry_price")}
          />
          {errors.entry_price && (
            <p className="mt-1 text-xs text-danger">{errors.entry_price.message}</p>
          )}
        </div>
        <div>
          <label htmlFor="stop_loss" className="mb-1 block text-sm text-text-secondary">
            Stop Loss
          </label>
          <input
            id="stop_loss"
            type="number"
            step="any"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("stop_loss")}
          />
          {errors.stop_loss && <p className="mt-1 text-xs text-danger">{errors.stop_loss.message}</p>}
        </div>
      </div>
    </div>
  );
}
