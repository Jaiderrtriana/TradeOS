import { z } from "zod";

/** `PATCH /playbook-setups/{id}` — all four fields are always sent
 * together (see `types.ts`'s `UpdatePlaybookSetupPayload` docstring):
 * every field is required at the schema level (never optional) so an
 * untouched field can never resolve to `undefined` and be dropped. */
export const updatePlaybookSetupSchema = z.object({
  entry_criteria: z.string(),
  exit_criteria: z.string(),
  ideal_conditions: z.string(),
  risk_rules: z.string(),
});
export type UpdatePlaybookSetupFormValues = z.output<typeof updatePlaybookSetupSchema>;

/** `POST /playbook-setups/{id}/attachments` — `file_reference` mirrors
 * the backend's own `min_length=1`; no URL-format validation is imposed
 * beyond that, since no frozen document specifies one. */
export const addPlaybookSetupAttachmentSchema = z.object({
  file_reference: z.string().min(1, "Enter a file reference (URL)."),
  caption: z.string().optional(),
});
export type AddPlaybookSetupAttachmentFormValues = z.output<
  typeof addPlaybookSetupAttachmentSchema
>;
