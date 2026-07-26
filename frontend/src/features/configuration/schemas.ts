import { z } from "zod";

/**
 * Client-side shape/range validation — TRADEOS_FRONTEND_BLUEPRINT.md §10:
 * "a fast-feedback client check, never the sole gate" (the backend
 * re-validates everything regardless). Limits mirror the real backend
 * schemas exactly (Field(max_length=...), Field(ge=0)).
 */

export const createDraftVersionSchema = z.object({
  version_label: z.string().min(1, "Enter a version label.").max(40, "Max 40 characters."),
});
export type CreateDraftVersionFormValues = z.infer<typeof createDraftVersionSchema>;

export const weightFormSchema = z.object({
  criterion_id: z.string().min(1, "Select a criterion."),
  profile_code: z.string().min(1, "Select a profile."),
  weight: z.coerce.number().min(0, "Weight must be 0 or greater."),
});
// z.coerce.number() has a different input (raw form value, e.g. string)
// and output (number) type — useForm is typed against the input shape,
// the resolver/submit handler against the output shape.
export type WeightFormInput = z.input<typeof weightFormSchema>;
export type WeightFormValues = z.output<typeof weightFormSchema>;

export const CATALOG_KIND_OPTIONS = [
  { value: "setup", label: "Setup" },
  { value: "session", label: "Session" },
  { value: "strategy", label: "Strategy" },
  { value: "entry_trigger", label: "Entry Trigger" },
  { value: "mistake_tag", label: "Mistake Tag" },
];

export const createCatalogEntrySchema = z.object({
  kind: z.enum(["setup", "session", "strategy", "entry_trigger", "mistake_tag"], {
    message: "Select a kind.",
  }),
  name: z.string().min(1, "Enter a name.").max(120, "Max 120 characters."),
});
export type CreateCatalogEntryFormValues = z.infer<typeof createCatalogEntrySchema>;

export const renameCatalogEntrySchema = z.object({
  name: z.string().min(1, "Enter a name.").max(120, "Max 120 characters."),
});
export type RenameCatalogEntryFormValues = z.infer<typeof renameCatalogEntrySchema>;
