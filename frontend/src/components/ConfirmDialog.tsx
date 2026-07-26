import * as RadixAlertDialog from "@radix-ui/react-alert-dialog";
import type { ReactNode } from "react";

/**
 * Shared confirmation dialog — TRADEOS_FRONTEND_BLUEPRINT.md §6.8: Publish
 * "confirm (Modal/Dialog, given irreversibility)". Built on Radix
 * AlertDialog specifically, not the generic Dialog primitive — the
 * stricter focus-trap/no-outside-dismiss semantics are the correct fit
 * for a consequential, hard-to-reverse action (TRADEOS_API_SPECIFICATION.md
 * §3.5: publishing a version is "irreversible in effect").
 */
export interface ConfirmDialogProps {
  trigger: ReactNode;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
  isConfirming?: boolean;
}

export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel,
  onConfirm,
  isConfirming = false,
}: ConfirmDialogProps) {
  return (
    <RadixAlertDialog.Root>
      <RadixAlertDialog.Trigger asChild>{trigger}</RadixAlertDialog.Trigger>
      <RadixAlertDialog.Portal>
        <RadixAlertDialog.Overlay className="fixed inset-0 bg-bg-base/80" />
        <RadixAlertDialog.Content className="fixed left-1/2 top-1/2 w-full max-w-sm -translate-x-1/2 -translate-y-1/2 rounded border border-border bg-bg-surface p-6">
          <RadixAlertDialog.Title className="text-base font-semibold text-text-primary">
            {title}
          </RadixAlertDialog.Title>
          <RadixAlertDialog.Description className="mt-2 text-sm text-text-secondary">
            {description}
          </RadixAlertDialog.Description>
          <div className="mt-6 flex justify-end gap-3">
            <RadixAlertDialog.Cancel asChild>
              <button
                type="button"
                className="rounded border border-border px-3 py-2 text-sm text-text-secondary"
              >
                Cancel
              </button>
            </RadixAlertDialog.Cancel>
            <RadixAlertDialog.Action asChild>
              <button
                type="button"
                onClick={onConfirm}
                disabled={isConfirming}
                className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
              >
                {isConfirming ? "Working…" : confirmLabel}
              </button>
            </RadixAlertDialog.Action>
          </div>
        </RadixAlertDialog.Content>
      </RadixAlertDialog.Portal>
    </RadixAlertDialog.Root>
  );
}
