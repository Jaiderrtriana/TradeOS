import * as RadixDialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

/**
 * Shared Modal/Dialog — TRADEOS_FRONTEND_BLUEPRINT.md §7: "Focused,
 * blocking interaction (confirmations, small forms)... New Trade (Simple
 * mode)." Built on Radix Dialog (not AlertDialog — that primitive is
 * `ConfirmDialog`'s, reserved for irreversible-action confirmations per
 * its own docstring); this one hosts arbitrary form content and needs
 * controlled open state so a mutation's `onSuccess` can close it
 * programmatically, which an uncontrolled `Trigger`-only dialog can't do.
 *
 * First consumer: Trade Entry (`TradeEntryModal`, Sprint 4.4) — also
 * reused for Amend/Close, and the Mistake-tag `CatalogPickerModal`.
 */
export interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
}

export function Modal({ open, onOpenChange, title, description, children }: ModalProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-bg-base/80" />
        <RadixDialog.Content className="fixed left-1/2 top-1/2 max-h-[90vh] w-full max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded border border-border bg-bg-surface p-6">
          <div className="flex items-start justify-between gap-4">
            <div>
              <RadixDialog.Title className="text-base font-semibold text-text-primary">
                {title}
              </RadixDialog.Title>
              {description && (
                <RadixDialog.Description className="mt-1 text-sm text-text-secondary">
                  {description}
                </RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close asChild>
              <button
                type="button"
                aria-label="Close"
                className="text-text-muted hover:text-text-primary"
              >
                ✕
              </button>
            </RadixDialog.Close>
          </div>
          <div className="mt-4">{children}</div>
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
