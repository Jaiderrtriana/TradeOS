import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError } from "../../../api/errors";
import { ConfirmDialog } from "../../../components/ConfirmDialog";
import { useErrorReporter } from "../../../components/ErrorContext";
import { deleteTrade } from "../api";
import { tradingKeys } from "../queryKeys";
import type { TradeDetail } from "../types";
import { AmendTradeModal } from "./AmendTradeModal";
import { CloseTradeModal } from "./CloseTradeModal";
import { OpenTradeModal } from "./OpenTradeModal";
import { ReevaluateModal } from "./ReevaluateModal";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.3's `ActionBar`: "Amend, Close, Re-
 * evaluate, Delete — each action opens its own Modal/Dialog." Delete is
 * soft (`DELETE /trades/{id}`, §6.4) — confirmed via the existing
 * `ConfirmDialog`, then navigates back to the Trades List since the Trade
 * Detail route it's currently on no longer resolves.
 *
 * v2.0 (Trade Entry redesign, Domain Model KDD-07): `Open` (new action,
 * `POST /trades/{id}/open`) is offered only while `status = planned`;
 * `Close` only while `status = open` (previously gated on the now-retired
 * `result === "open"`); `Re-evaluate` only once an Evaluation actually
 * exists, i.e. `status != planned` (Domain Invariant DI-13 — a Planned
 * Trade has no Evaluation to re-run yet).
 */
export function ActionBar({ trade }: { trade: TradeDetail }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [amendOpen, setAmendOpen] = useState(false);
  const [openTradeOpen, setOpenTradeOpen] = useState(false);
  const [closeOpen, setCloseOpen] = useState(false);
  const [reevaluateOpen, setReevaluateOpen] = useState(false);

  const remove = useMutation({
    mutationFn: () => deleteTrade(trade.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.list({}) });
      navigate("/trades");
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <div className="flex flex-wrap gap-3">
      <button
        type="button"
        onClick={() => setAmendOpen(true)}
        className="rounded border border-border px-3 py-2 text-sm text-text-primary"
      >
        Amend
      </button>
      {trade.status === "planned" && (
        <button
          type="button"
          onClick={() => setOpenTradeOpen(true)}
          className="rounded border border-border px-3 py-2 text-sm text-text-primary"
        >
          Open
        </button>
      )}
      {trade.status === "open" && (
        <button
          type="button"
          onClick={() => setCloseOpen(true)}
          className="rounded border border-border px-3 py-2 text-sm text-text-primary"
        >
          Close
        </button>
      )}
      {trade.status !== "planned" && (
        <button
          type="button"
          onClick={() => setReevaluateOpen(true)}
          className="rounded border border-border px-3 py-2 text-sm text-text-primary"
        >
          Re-evaluate
        </button>
      )}
      <ConfirmDialog
        trigger={
          <button type="button" className="rounded border border-border px-3 py-2 text-sm text-danger">
            Delete
          </button>
        }
        title="Delete this trade?"
        description="This is a soft delete — the Trade's Checklist, Evaluation Snapshots, and Journal references remain in storage. This is for a genuine data-entry mistake, not for closing a trade."
        confirmLabel="Delete"
        onConfirm={() => remove.mutate()}
        isConfirming={remove.isPending}
      />

      <AmendTradeModal trade={trade} open={amendOpen} onOpenChange={setAmendOpen} />
      <OpenTradeModal
        tradeId={trade.id}
        direction={trade.direction}
        open={openTradeOpen}
        onOpenChange={setOpenTradeOpen}
      />
      <CloseTradeModal tradeId={trade.id} open={closeOpen} onOpenChange={setCloseOpen} />
      <ReevaluateModal tradeId={trade.id} open={reevaluateOpen} onOpenChange={setReevaluateOpen} />
    </div>
  );
}
