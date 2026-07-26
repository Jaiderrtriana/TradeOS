/**
 * Shared status Badge — TRADEOS_FRONTEND_BLUEPRINT.md §7 ("Badge: Small
 * status/label indicator... Nearly every table and detail page"), §14
 * ("a small, fixed set of elevation levels... not a continuous,
 * page-specific choice"). Built only from the color tokens already
 * defined in tailwind.config.ts (no new Design System tokens added this
 * sprint) — "accent" reads as the positive/current state (published,
 * active), "muted" as a past/inactive state (superseded, inactive), and a
 * plain bordered variant as a neutral/in-progress state (draft).
 */
export type BadgeTone = "accent" | "muted" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  accent: "border-accent/40 bg-accent/10 text-text-primary",
  muted: "border-border bg-bg-overlay text-text-muted",
  neutral: "border-border bg-transparent text-text-secondary",
};

export interface BadgeProps {
  label: string;
  tone: BadgeTone;
}

export function Badge({ label, tone }: BadgeProps) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {label}
    </span>
  );
}
