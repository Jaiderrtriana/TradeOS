import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Modal } from "../../../components/Modal";
import { Select } from "../../../components/Select";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { listScoringProfiles, scoringReferenceKeys } from "../../../shared/scoringReferenceData";

export interface TradeTypeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (profileCode: string) => void;
}

/**
 * Just-in-time Trade Type prompt — approved resolution from the Trade
 * Entry redesign review ("Option 4"): Scoring Profile ("Trade Type")
 * stays a required field once a Trade isn't Planned (Domain Model KDD-07,
 * Sprint 4.1's original decision that it must be part of the explicit
 * context every scored Trade is registered with — never a silent default,
 * never made optional). Rather than blocking the whole form up front,
 * this dialog only appears at the moment of submission, if the field was
 * left empty — a lighter-weight nudge than an inline required-field error
 * for what is, in the Simple flow, often the very last thing a fast-
 * moving trader fills in.
 *
 * Deliberately its own independent component, not built on
 * `ConfirmDialog` (reserved for irreversible-action confirmations, see
 * that component's own docstring) — this dialog collects a real input
 * value and hands it back via `onSelect`, a shape `ConfirmDialog` doesn't
 * support. Built on the shared `Modal` primitive instead, same as every
 * other Trading dialog (`TradeEntryModal`/`AmendTradeModal`/
 * `CloseTradeModal`/`OpenTradeModal`).
 */
export function TradeTypeDialog({ open, onOpenChange, onSelect }: TradeTypeDialogProps) {
  const [profileCode, setProfileCode] = useState("");

  const { data: profiles } = useQuery({
    queryKey: scoringReferenceKeys.profiles(),
    queryFn: listScoringProfiles,
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  function handleContinue() {
    if (!profileCode) {
      return;
    }
    onSelect(profileCode);
    setProfileCode("");
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Select a Trade Type"
      description="A Trade Type determines which criteria this trade is evaluated against. Pick one to continue saving."
    >
      <div className="flex flex-col gap-4">
        <Select
          value={profileCode}
          onValueChange={setProfileCode}
          options={(profiles ?? []).map((p) => ({ value: p.code, label: p.display_name }))}
          aria-label="Trade Type"
        />
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded border border-border px-3 py-2 text-sm text-text-secondary"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleContinue}
            disabled={!profileCode}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            Continue
          </button>
        </div>
      </div>
    </Modal>
  );
}
