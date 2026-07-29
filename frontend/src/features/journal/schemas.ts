import { z } from "zod";

/**
 * Client-side shape validation — TRADEOS_FRONTEND_BLUEPRINT.md §10:
 * "a fast-feedback client check, never the sole gate." No length limit
 * is mirrored on `content` because the backend defines none
 * (`content TEXT NOT NULL`, no `CHECK` — `TRADEOS_DATABASE_DESIGN.md`
 * §6.17). No period-ordering check (`period_end >= period_start`) either
 * — the backend's own check constraint doesn't enforce one, and this
 * form does not invent a rule the API doesn't have.
 */

export const journalContentSchema = z.object({
  content: z.string().min(1, "Enter some content."),
});
export type JournalContentFormValues = z.infer<typeof journalContentSchema>;

export const periodJournalEntrySchema = z.object({
  content: z.string().min(1, "Enter some content."),
  period_start: z.string().min(1, "Select a start date."),
  period_end: z.string().min(1, "Select an end date."),
});
export type PeriodJournalEntryFormValues = z.infer<typeof periodJournalEntrySchema>;
