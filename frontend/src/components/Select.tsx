import * as RadixSelect from "@radix-ui/react-select";

/**
 * Shared Select — TRADEOS_TECHNICAL_STACK.md §6.5 (Radix UI Primitives):
 * accessible behavior (focus, keyboard nav, ARIA roles) without a
 * pre-baked visual opinion, per TRADEOS_FRONTEND_BLUEPRINT.md §14/§15.
 * Reused by every dropdown this project needs — first consumer is
 * PreferencesPage's theme/language selectors.
 */
export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  options: SelectOption[];
  "aria-label": string;
}

export function Select({ value, onValueChange, options, ...ariaProps }: SelectProps) {
  return (
    <RadixSelect.Root value={value} onValueChange={onValueChange}>
      <RadixSelect.Trigger
        className="flex w-48 items-center justify-between rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
        aria-label={ariaProps["aria-label"]}
      >
        <RadixSelect.Value />
        <RadixSelect.Icon>▾</RadixSelect.Icon>
      </RadixSelect.Trigger>
      <RadixSelect.Portal>
        <RadixSelect.Content className="overflow-hidden rounded border border-border bg-bg-surface text-sm text-text-primary">
          <RadixSelect.Viewport className="p-1">
            {options.map((option) => (
              <RadixSelect.Item
                key={option.value}
                value={option.value}
                className="cursor-pointer rounded px-3 py-2 outline-none data-[highlighted]:bg-bg-overlay"
              >
                <RadixSelect.ItemText>{option.label}</RadixSelect.ItemText>
              </RadixSelect.Item>
            ))}
          </RadixSelect.Viewport>
        </RadixSelect.Content>
      </RadixSelect.Portal>
    </RadixSelect.Root>
  );
}
