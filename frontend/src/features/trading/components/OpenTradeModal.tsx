import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo } from "react";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { listScoringProfiles, scoringReferenceKeys } from "../../../shared/scoringReferenceData";
import { dateOnlyToAwareIso, usePreferencesTimezone } from "../../../shared/timezone";
import { openTrade } from "../api";
import { tradingKeys } from "../queryKeys";
import {
  buildOpenTradeSchema,
  type OpenTradeFormInput,
  type OpenTradeFormValues,
} from "../schemas";
import type { Direction } from "../types";

/**
 * `POST /trades/{id}/open` (new in v2.0, Trade Entry redesign) — the
 * `Planned → Open` transition action, surfaced from `ActionBar` only
 * while `trade.status === "planned"` (mirrors `CloseTradeModal`'s own
 * `trade.status === "open"` gating for `Close`). Triggers Evaluation for
 * the first time, so `scoring_profile` ("Trade Type") is required here
 * exactly as it is for a Trade registered directly as `Open`.
 */
export function OpenTradeModal({
  tradeId,
  direction,
  open,
  onOpenChange,
}: {
  tradeId: string;
  direction: Direction;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const timezone = usePreferencesTimezone();
  const schema = useMemo(() => buildOpenTradeSchema(direction), [direction]);

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<OpenTradeFormInput, unknown, OpenTradeFormValues>({
    resolver: zodResolver(schema),
  });

  const openMutation = useMutation({
    // `values.entered_at` is a date-only string ("2026-01-01") from the
    // `<input type="date">` below — anchored to the resolved timezone
    // before it ever reaches the API, never left for the backend to
    // guess (Sprint 4 Fase 2, OQ-7 contract; `!` is safe here, the
    // schema already requires this field non-empty).
    mutationFn: (values: OpenTradeFormValues) =>
      openTrade(tradeId, {
        ...values,
        entered_at: dateOnlyToAwareIso(values.entered_at, timezone)!,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.detail(tradeId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => {
      if (error.status === 409) {
        reportError(
          new ApiError({ status: 409, code: error.code, message: "This trade is not planned." }),
        );
        return;
      }
      reportError(error);
    },
  });

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Open Trade"
      description="This is the first moment the trade becomes a real, executed position — it also runs the Evaluation for the first time."
    >
      <form
        onSubmit={handleSubmit((values) => openMutation.mutate(values))}
        className="flex flex-col gap-4"
      >
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
            <label htmlFor="open-entry-price" className="mb-1 block text-sm text-text-secondary">
              Entry Price
            </label>
            <input
              id="open-entry-price"
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
            <label htmlFor="open-stop-loss" className="mb-1 block text-sm text-text-secondary">
              Stop Loss
            </label>
            <input
              id="open-stop-loss"
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
            <label htmlFor="open-take-profit" className="mb-1 block text-sm text-text-secondary">
              Take Profit
            </label>
            <input
              id="open-take-profit"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("take_profit")}
            />
          </div>
        </div>

        <div>
          <label htmlFor="open-entered-at" className="mb-1 block text-sm text-text-secondary">
            Entry Date
          </label>
          <input
            id="open-entered-at"
            type="date"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("entered_at")}
          />
          {errors.entered_at && (
            <p className="mt-1 text-xs text-danger">{errors.entered_at.message}</p>
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
            disabled={openMutation.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {openMutation.isPending ? "Opening…" : "Open Trade"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
