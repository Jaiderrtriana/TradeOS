import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { amendTrade } from "../api";
import { tradingKeys } from "../queryKeys";
import { amendTradeSchema, type AmendTradeFormInput, type AmendTradeFormValues } from "../schemas";
import type { TradeDetail } from "../types";

const DIRECTION_OPTIONS = [
  { value: "long", label: "Long" },
  { value: "short", label: "Short" },
];

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §10's Trade Amendment row: "a visible
 * note that this action logs a `TradeAmended` event (transparency, not a
 * silent edit)." Pre-filled from the current Trade — `PATCH /trades/{id}`
 * re-validates the *proposed full state*, so this form always submits
 * every field, not just the ones the user touched.
 */
export function AmendTradeModal({
  trade,
  open,
  onOpenChange,
}: {
  trade: TradeDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<AmendTradeFormInput, unknown, AmendTradeFormValues>({
    resolver: zodResolver(amendTradeSchema),
    defaultValues: {
      market: trade.market,
      direction: trade.direction,
      entry_price: trade.entry_price,
      stop_loss: trade.stop_loss,
      size: trade.size,
      leverage: trade.leverage,
      notes: trade.notes,
      strategy_id: trade.strategy_id ?? undefined,
      setup_id: trade.setup_id ?? undefined,
      session_id: trade.session_id ?? undefined,
      entry_trigger_id: trade.entry_trigger_id ?? undefined,
      mfe_price: trade.mfe_price ?? undefined,
      mae_price: trade.mae_price ?? undefined,
    },
  });

  const amend = useMutation({
    mutationFn: (values: AmendTradeFormValues) => amendTrade(trade.id, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.detail(trade.id) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      onOpenChange(false);
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Amend Trade"
      description="This logs a TradeAmended event — it does not re-run the Evaluation. Use Re-evaluate separately if the change should affect scoring."
    >
      <form onSubmit={handleSubmit((values) => amend.mutate(values))} className="flex flex-col gap-4">
        <div>
          <label htmlFor="amend-market" className="mb-1 block text-sm text-text-secondary">
            Market
          </label>
          <input
            id="amend-market"
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
          </div>
          <div>
            <label htmlFor="amend-size" className="mb-1 block text-sm text-text-secondary">
              Size
            </label>
            <input
              id="amend-size"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("size")}
            />
            {errors.size && <p className="mt-1 text-xs text-danger">{errors.size.message}</p>}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="amend-entry-price" className="mb-1 block text-sm text-text-secondary">
              Entry Price
            </label>
            <input
              id="amend-entry-price"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("entry_price")}
            />
          </div>
          <div>
            <label htmlFor="amend-stop-loss" className="mb-1 block text-sm text-text-secondary">
              Stop Loss
            </label>
            <input
              id="amend-stop-loss"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("stop_loss")}
            />
            {errors.stop_loss && (
              <p className="mt-1 text-xs text-danger">{errors.stop_loss.message}</p>
            )}
          </div>
        </div>

        <div>
          <label htmlFor="amend-notes" className="mb-1 block text-sm text-text-secondary">
            Notes
          </label>
          <textarea
            id="amend-notes"
            rows={3}
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("notes")}
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
            disabled={amend.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {amend.isPending ? "Saving…" : "Save Changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
