import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";

import { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { listScoringProfiles, scoringReferenceKeys } from "../../../shared/scoringReferenceData";
import { reevaluateTrade } from "../api";
import { tradingKeys } from "../queryKeys";
import {
  reevaluateTradeSchema,
  type ReevaluateTradeFormValues,
} from "../schemas";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §6.6's Re-evaluate flow: "confirm (a
 * Modal/Dialog... this action's consequence, creating a new permanent
 * snapshot, warrants an explicit confirmation step even though the API
 * itself requires no confirmation payload)." The API *does* require
 * `scoring_profile` (§6.4's `ReevaluateTradeRequest`), so this
 * confirmation carries that one field — `configuration_version_id` is
 * intentionally not exposed (see `schemas.ts`'s docstring). The prior
 * snapshot is never deleted (§6.6: "remains reachable via History").
 */
export function ReevaluateModal({
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

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ReevaluateTradeFormValues>({
    resolver: zodResolver(reevaluateTradeSchema),
    defaultValues: { scoring_profile: "" },
  });

  const reevaluate = useMutation({
    mutationFn: (values: ReevaluateTradeFormValues) => reevaluateTrade(tradeId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.detail(tradeId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.evaluation(tradeId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.evaluationHistory(tradeId) });
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Re-evaluate Trade"
      description="This creates a new permanent Evaluation Snapshot. The current one is kept in History, never deleted."
    >
      <form
        onSubmit={handleSubmit((values) => reevaluate.mutate(values))}
        className="flex flex-col gap-4"
      >
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
            disabled={reevaluate.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {reevaluate.isPending ? "Re-evaluating…" : "Re-evaluate"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
