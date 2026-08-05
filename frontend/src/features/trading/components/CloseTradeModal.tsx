import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { closeTrade } from "../api";
import { tradingKeys } from "../queryKeys";
import { closeTradeSchema, type CloseTradeFormInput, type CloseTradeFormValues } from "../schemas";

const RESULT_OPTIONS = [
  { value: "tp", label: "Take Profit" },
  { value: "sl", label: "Stop Loss" },
  { value: "be", label: "Break Even" },
];

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §6.4/§10's Trade Close row: "Requires
 * `result` + `exit_price` together, mirrored client-side before submit
 * (INV-TRADE-02)" — both are required fields of `closeTradeSchema`
 * structurally, so that invariant can't be violated from this form.
 * A `409` (already closed) is shown as a state-conflict message, not a
 * generic error (§10).
 */
export function CloseTradeModal({
  tradeId,
  open,
  onOpenChange,
}: {
  tradeId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CloseTradeFormInput, unknown, CloseTradeFormValues>({
    resolver: zodResolver(closeTradeSchema),
  });

  const close = useMutation({
    mutationFn: (values: CloseTradeFormValues) => closeTrade(tradeId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.detail(tradeId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => {
      if (error.status === 409) {
        reportError(
          new ApiError({
            status: 409,
            code: error.code,
            message: "This trade is already closed.",
          }),
        );
        return;
      }
      reportError(error);
    },
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title="Close Trade">
      <form onSubmit={handleSubmit((values) => close.mutate(values))} className="flex flex-col gap-4">
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

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="close-exit-price" className="mb-1 block text-sm text-text-secondary">
              Exit Price
            </label>
            <input
              id="close-exit-price"
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
            <label htmlFor="close-realized-pnl" className="mb-1 block text-sm text-text-secondary">
              Realized P&amp;L
            </label>
            <input
              id="close-realized-pnl"
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

        <div>
          <label htmlFor="close-closed-at" className="mb-1 block text-sm text-text-secondary">
            Close Date
          </label>
          <input
            id="close-closed-at"
            type="date"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("closed_at")}
          />
          {errors.closed_at && (
            <p className="mt-1 text-xs text-danger">{errors.closed_at.message}</p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="close-mfe-price" className="mb-1 block text-sm text-text-secondary">
              MFE Price
            </label>
            <input
              id="close-mfe-price"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("mfe_price")}
            />
          </div>
          <div>
            <label htmlFor="close-mae-price" className="mb-1 block text-sm text-text-secondary">
              MAE Price
            </label>
            <input
              id="close-mae-price"
              type="number"
              step="any"
              className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
              {...register("mae_price")}
            />
          </div>
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
            disabled={close.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {close.isPending ? "Closing…" : "Close Trade"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
