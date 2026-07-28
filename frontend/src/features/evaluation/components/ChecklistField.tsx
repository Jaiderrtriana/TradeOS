import { Select } from "../../../components/Select";
import type { ScoringCriterion } from "../../../shared/scoringReferenceData";

/**
 * One checklist question, rendered from real Configuration data
 * (TRADEOS_API_SPECIFICATION.md §6.6) — never a hardcoded question list.
 * `category_map` present → a Select of the real category labels
 * (`checklist_answers` carries the label itself, TRADEOS_DATABASE_DESIGN.md
 * §6.5's `category_map JSONB` — never a pre-normalized number, per the
 * Sprint 3.2 correction this API already relies on). `category_map` absent
 * → a plain numeric input bounded by the criterion's own real
 * `min_value`/`max_value` (client-side range hint only, per
 * TRADEOS_FRONTEND_BLUEPRINT.md Principle 2 — the backend remains the
 * real gate).
 */
export interface ChecklistFieldProps {
  criterion: ScoringCriterion;
  value: string | number | undefined;
  onChange: (value: string | number | undefined) => void;
}

export function ChecklistField({ criterion, value, onChange }: ChecklistFieldProps) {
  const fieldId = `checklist-${criterion.id}`;

  if (criterion.category_map) {
    const options = Object.keys(criterion.category_map).map((label) => ({
      value: label,
      label,
    }));
    return (
      <div>
        <p className="mb-1 text-sm text-text-secondary">{criterion.name}</p>
        <Select
          value={typeof value === "string" ? value : ""}
          onValueChange={(next) => onChange(next === "" ? undefined : next)}
          options={options}
          aria-label={criterion.name}
        />
      </div>
    );
  }

  return (
    <div>
      <label htmlFor={fieldId} className="mb-1 block text-sm text-text-secondary">
        {criterion.name}
      </label>
      <input
        id={fieldId}
        type="number"
        step="any"
        min={criterion.min_value}
        max={criterion.max_value}
        value={value ?? ""}
        onChange={(event) => {
          const raw = event.target.value;
          onChange(raw === "" ? undefined : Number(raw));
        }}
        className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
      />
    </div>
  );
}
