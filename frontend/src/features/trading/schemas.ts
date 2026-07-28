import { z } from "zod";

/**
 * Client-side shape/range validation — TRADEOS_FRONTEND_BLUEPRINT.md §10:
 * "a fast-feedback client check, never the sole gate" (the backend
 * re-validates everything regardless). `entryStopSideRefine` mirrors
 * INV-TRADE-01 exactly (`TRADEOS_DATABASE_DESIGN.md` §6.9's check
 * constraint: stop must be on the correct side of entry for the given
 * direction) — a well-defined, already-shipped domain rule, not an
 * invented one.
 *
 * One schema for both Simple and Pro Trade Entry (`TRADEOS_FRONTEND_
 * BLUEPRINT.md` Principle 7: "the frontend must offer a 'Simple' path
 * that asks for only the required fields, and a 'Pro' path that surfaces
 * everything... never only the maximal form") — Simple mode's form
 * registers only the required subset of these same fields; Pro mode
 * registers all of them plus the checklist, both validated by this one
 * schema so switching modes never silently drops a validation rule.
 */

function entryStopSideRefine<
  T extends { direction: "long" | "short"; entry_price: number; stop_loss: number },
>(values: T, ctx: z.RefinementCtx) {
  const valid =
    values.direction === "long"
      ? values.stop_loss < values.entry_price
      : values.stop_loss > values.entry_price;
  if (!valid) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["stop_loss"],
      message:
        values.direction === "long"
          ? "For a long trade, stop loss must be below entry price."
          : "For a short trade, stop loss must be above entry price.",
    });
  }
}

export const tradeEntrySchema = z
  .object({
    market: z.string().min(1, "Enter a market.").max(20, "Max 20 characters."),
    direction: z.enum(["long", "short"], { message: "Select a direction." }),
    entry_price: z.coerce.number({ message: "Enter an entry price." }),
    stop_loss: z.coerce.number({ message: "Enter a stop loss." }),
    scoring_profile: z.string().min(1, "Select a scoring profile."),
    exit_price: z.coerce.number().optional(),
    size: z.coerce.number().min(0, "Size must be 0 or greater.").optional(),
    leverage: z.string().max(10, "Max 10 characters.").optional(),
    result: z.enum(["open", "tp", "sl", "be"]).optional(),
    strategy_id: z.string().optional(),
    setup_id: z.string().optional(),
    session_id: z.string().optional(),
    entry_trigger_id: z.string().optional(),
    notes: z.string().optional(),
    mfe_price: z.coerce.number().optional(),
    mae_price: z.coerce.number().optional(),
  })
  .superRefine(entryStopSideRefine);
export type TradeEntryFormInput = z.input<typeof tradeEntrySchema>;
export type TradeEntryFormValues = z.output<typeof tradeEntrySchema>;

/** `PATCH /trades/{id}` — every field optional, re-validated as a whole
 * proposed state (`TRADEOS_FRONTEND_BLUEPRINT.md` §10's Trade Amendment
 * row: "re-checked against the *proposed full state*"). */
export const amendTradeSchema = z
  .object({
    market: z.string().min(1, "Enter a market.").max(20, "Max 20 characters.").optional(),
    direction: z.enum(["long", "short"]).optional(),
    entry_price: z.coerce.number().optional(),
    stop_loss: z.coerce.number().optional(),
    size: z.coerce.number().min(0, "Size must be 0 or greater.").optional(),
    leverage: z.string().max(10, "Max 10 characters.").optional(),
    notes: z.string().optional(),
    strategy_id: z.string().optional(),
    setup_id: z.string().optional(),
    session_id: z.string().optional(),
    entry_trigger_id: z.string().optional(),
    mfe_price: z.coerce.number().optional(),
    mae_price: z.coerce.number().optional(),
  })
  .superRefine((values, ctx) => {
    if (values.direction && values.entry_price !== undefined && values.stop_loss !== undefined) {
      entryStopSideRefine(
        { direction: values.direction, entry_price: values.entry_price, stop_loss: values.stop_loss },
        ctx,
      );
    }
  });
export type AmendTradeFormInput = z.input<typeof amendTradeSchema>;
export type AmendTradeFormValues = z.output<typeof amendTradeSchema>;

/** `POST /trades/{id}/close` — INV-TRADE-02 (`result` and `exit_price`
 * required together) is satisfied structurally here: both are always
 * required fields of this schema, never independently optional. */
export const closeTradeSchema = z.object({
  result: z.enum(["tp", "sl", "be"], { message: "Select a result." }),
  exit_price: z.coerce.number({ message: "Enter an exit price." }),
  mfe_price: z.coerce.number().optional(),
  mae_price: z.coerce.number().optional(),
});
export type CloseTradeFormInput = z.input<typeof closeTradeSchema>;
export type CloseTradeFormValues = z.output<typeof closeTradeSchema>;

/** `POST /trades/{id}/reevaluate` — `scoring_profile` is required (same
 * approved resolution as `POST /trades`, see `backend/.../schemas.py`);
 * `configuration_version_id` is intentionally not exposed in the UI —
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §6.6's Re-evaluate flow names no such
 * field, and the API defaults to the currently published version when
 * omitted. */
export const reevaluateTradeSchema = z.object({
  scoring_profile: z.string().min(1, "Select a scoring profile."),
});
export type ReevaluateTradeFormValues = z.infer<typeof reevaluateTradeSchema>;
