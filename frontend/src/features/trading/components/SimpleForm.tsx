import { useQuery } from "@tanstack/react-query";
import { Controller, useFormContext, useWatch } from "react-hook-form";

import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { listScoringProfiles, scoringReferenceKeys } from "../../../shared/scoringReferenceData";
import type { TradeEntryFormInput, TradeEntryFormValues } from "../schemas";

const DIRECTION_OPTIONS = [
  { value: "long", label: "Long" },
  { value: "short", label: "Short" },
];

const STATUS_OPTIONS = [
  { value: "planned", label: "Planned" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
];

const RESULT_OPTIONS = [
  { value: "tp", label: "Take Profit" },
  { value: "sl", label: "Stop Loss" },
  { value: "be", label: "Break Even" },
];

/**
 * Simple Trade Entry — `TRADEOS_FRONTEND_BLUEPRINT.md` Principle 7: "a
 * 'Simple' path that asks for only the required fields." Reads the shared
 * `useTradeEntryForm` context via `useFormContext`, so switching to Pro
 * mode never loses what was typed here.
 *
 * v2.0 (Trade Entry redesign, Domain Model KDD-07): rebuilt around the
 * new `status` field (Excel-sourced "Estado" column, `📒 Trades simple`
 * sheet) — field visibility is fully dynamic per status, mirroring
 * INV-TRADE-02 exactly (never a superset or subset of what the backend
 * actually requires/accepts for a given status):
 *
 * - `planned`: only Market/Direction/Status — no entry facts exist yet.
 * - `open`: adds Trade Type, Entry Price, Stop Loss, Take Profit, Entry
 *   Date — the position is live, but not yet closed.
 * - `closed`: adds Exit Price, Result, Close Date, Realized P&L — the
 *   full backfill-a-historical-trade shape.
 *
 * "Trade Type" is this form's label for `scoring_profile` (approved
 * rename, Trade Entry redesign review) — still the same wire field, still
 * required once `status != planned` (Sprint 4.1's original KDD, unchanged
 * by the rename). If left empty at submit time, `TradeTypeDialog` prompts
 * for it just-in-time rather than blocking the field inline — wired in
 * `TradeEntryModal`, not here (this component only renders the field).
 */
export function SimpleForm() {
  const {
    register,
    control,
    setValue,
    formState: { errors },
  } = useFormContext<TradeEntryFormInput, unknown, TradeEntryFormValues>();

  const status = useWatch({ control, name: "status" });

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  function handleStatusChange(nextStatus: string) {
    setValue("status", nextStatus as TradeEntryFormValues["status"]);
    if (nextStatus === "planned") {
      // INV-TRADE-02: a planned trade must not carry entry/close facts --
      // clear them so a value typed before switching back to Planned
      // doesn't silently ride along in the submitted payload.
      setValue("scoring_profile", "");
      setValue("entry_price", undefined);
      setValue("stop_loss", undefined);
      setValue("take_profit", undefined);
      setValue("entered_at", "");
    }
    if (nextStatus !== "closed") {
      setValue("exit_price", undefined);
      setValue("result", undefined);
      setValue("closed_at", "");
      setValue("realized_pnl", undefined);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-4">
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
        <div>
          <p className="mb-1 text-sm text-text-secondary">Trade Status</p>
          <Controller
            name="status"
            control={control}
            render={({ field }) => (
              <Select
                value={field.value ?? ""}
                onValueChange={handleStatusChange}
                options={STATUS_OPTIONS}
                aria-label="Trade Status"
              />
            )}
          />
          {errors.status && <p className="mt-1 text-xs text-danger">{errors.status.message}</p>}
        </div>
      </div>

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
        {errors.direction && <p className="mt-1 text-xs text-danger">{errors.direction.message}</p>}
      </div>

      {status !== "planned" && (
        <>
          <div>
            <p className="mb-1 text-sm text-text-secondary">Trade Type</p>
            <Controller
              name="scoring_profile"
              control={control}
              render={({ field }) => (
                <Select
                  value={field.value ?? ""}
                  onValueChange={field.onChange}
                  options={(profiles ?? []).map((p) => ({ value: p.code, label: p.display_name }))}
                  aria-label="Trade Type"
                />
              )}
            />
            {errors.scoring_profile && (
              <p className="mt-1 text-xs text-danger">{errors.scoring_profile.message}</p>
            )}
          </div>

          <div className="grid grid-cols-3 gap-4">
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
              {errors.stop_loss && (
                <p className="mt-1 text-xs text-danger">{errors.stop_loss.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="take_profit" className="mb-1 block text-sm text-text-secondary">
                Take Profit
              </label>
              <input
                id="take_profit"
                type="number"
                step="any"
                className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
                {...register("take_profit")}
              />
            </div>
          </div>

          <div>
            <label htmlFor="entered_at" className="mb-1 block text-sm text-text-secondary">
              Entry Date
            </label>
            <input
              id="entered_at"
              type="date"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("entered_at")}
            />
            {errors.entered_at && (
              <p className="mt-1 text-xs text-danger">{errors.entered_at.message}</p>
            )}
          </div>
        </>
      )}

      {status === "closed" && (
        <>
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
              {errors.exit_price && (
                <p className="mt-1 text-xs text-danger">{errors.exit_price.message}</p>
              )}
            </div>
            <div>
              <p className="mb-1 text-sm text-text-secondary">Result</p>
              <Controller
                name="result"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value ?? ""}
                    onValueChange={field.onChange}
                    options={RESULT_OPTIONS}
                    aria-label="Result"
                  />
                )}
              />
              {errors.result && <p className="mt-1 text-xs text-danger">{errors.result.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="closed_at" className="mb-1 block text-sm text-text-secondary">
                Close Date
              </label>
              <input
                id="closed_at"
                type="date"
                className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
                {...register("closed_at")}
              />
              {errors.closed_at && (
                <p className="mt-1 text-xs text-danger">{errors.closed_at.message}</p>
              )}
            </div>
            <div>
              <label htmlFor="realized_pnl" className="mb-1 block text-sm text-text-secondary">
                Realized P&amp;L
              </label>
              <input
                id="realized_pnl"
                type="number"
                step="any"
                className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
                {...register("realized_pnl")}
              />
              {errors.realized_pnl && (
                <p className="mt-1 text-xs text-danger">{errors.realized_pnl.message}</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
