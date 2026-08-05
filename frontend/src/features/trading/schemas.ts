import { z } from "zod";

/**
 * Client-side shape/range validation — TRADEOS_FRONTEND_BLUEPRINT.md §10:
 * "a fast-feedback client check, never the sole gate" (the backend
 * re-validates everything regardless). `checkStopSide` mirrors
 * INV-TRADE-01 exactly (`TRADEOS_DATABASE_DESIGN.md` §6.9's check
 * constraint: stop must be on the correct side of entry for the given
 * direction) — a well-defined, already-shipped domain rule, not an
 * invented one. Only runs once both `entry_price`/`stop_loss` are present
 * (v2.0: both are now optional at every status — a `Planned` Trade has
 * neither yet).
 *
 * One schema for both Simple and Pro Trade Entry (`TRADEOS_FRONTEND_
 * BLUEPRINT.md` Principle 7: "the frontend must offer a 'Simple' path
 * that asks for only the required fields, and a 'Pro' path that surfaces
 * everything... never only the maximal form") — Simple mode's form
 * registers only the required subset of these same fields; Pro mode
 * registers all of them plus the checklist, both validated by this one
 * schema so switching modes never silently drops a validation rule.
 *
 * v2.0 (Trade Entry redesign, Domain Model KDD-07): which fields are
 * actually required is now conditional on `status` (INV-TRADE-02,
 * redefined) — enforced here via `superRefine`, mirroring the backend's
 * own `Trade.__post_init__`/`validate_status_fields` exactly, so the
 * client never rejects (or accepts) a shape the server would disagree
 * with.
 */

export const TRADE_STATUSES = ["planned", "open", "closed"] as const;
export const RESULT_VALUES = ["tp", "sl", "be"] as const;

/** An optional `<input type="date">` left untouched submits `""`, not
 * `undefined` (RHF reads the DOM value directly) — without this, an
 * empty `entered_at`/`closed_at` would reach the API as `""`, which the
 * backend's `datetime` field rejects ("too short") instead of treating
 * as simply absent. */
const optionalDateString = z
  .string()
  .optional()
  .transform((value) => (value ? value : undefined));

function checkStopSide(
  direction: "long" | "short" | undefined,
  entryPrice: number | undefined,
  stopLoss: number | undefined,
  ctx: z.RefinementCtx,
) {
  if (direction === undefined || entryPrice === undefined || stopLoss === undefined) {
    return;
  }
  const valid = direction === "long" ? stopLoss < entryPrice : stopLoss > entryPrice;
  if (!valid) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["stop_loss"],
      message:
        direction === "long"
          ? "For a long trade, stop loss must be below entry price."
          : "For a short trade, stop loss must be above entry price.",
    });
  }
}

export const tradeEntrySchema = z
  .object({
    market: z.string().min(1, "Enter a market.").max(20, "Max 20 characters."),
    direction: z.enum(["long", "short"], { message: "Select a direction." }),
    status: z.enum(TRADE_STATUSES, { message: "Select a trade status." }),
    // Required unless status = planned (checked below).
    scoring_profile: z.string().optional(),
    entry_price: z.coerce.number().optional(),
    stop_loss: z.coerce.number().optional(),
    take_profit: z.coerce.number().optional(),
    entered_at: optionalDateString,
    // Required additionally when status = closed (checked below).
    exit_price: z.coerce.number().optional(),
    result: z.enum(RESULT_VALUES).optional(),
    closed_at: optionalDateString,
    realized_pnl: z.coerce.number().optional(),
    size: z.coerce.number().min(0, "Size must be 0 or greater.").optional(),
    margin_used: z.coerce.number().optional(),
    leverage: z.string().max(10, "Max 10 characters.").optional(),
    strategy_id: z.string().optional(),
    setup_id: z.string().optional(),
    session_id: z.string().optional(),
    entry_trigger_id: z.string().optional(),
    notes: z.string().optional(),
    mfe_price: z.coerce.number().optional(),
    mae_price: z.coerce.number().optional(),
  })
  .superRefine((values, ctx) => {
    if (values.status === "planned") {
      // INV-TRADE-02: a planned trade must not carry entry/close facts.
      if (values.entry_price !== undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["entry_price"],
          message: "A planned trade cannot have an entry price yet.",
        });
      }
    } else {
      if (!values.scoring_profile) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["scoring_profile"],
          message: "Select a trade type.",
        });
      }
      if (values.entry_price === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["entry_price"],
          message: "Enter an entry price.",
        });
      }
      if (!values.entered_at) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["entered_at"],
          message: "Enter the entry date.",
        });
      }
    }
    if (values.status === "closed") {
      if (values.exit_price === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["exit_price"],
          message: "Enter an exit price.",
        });
      }
      if (!values.result) {
        ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["result"], message: "Select a result." });
      }
      if (!values.closed_at) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["closed_at"],
          message: "Enter the close date.",
        });
      }
      if (values.realized_pnl === undefined) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ["realized_pnl"],
          message: "Enter the realized P&L.",
        });
      }
    }
    checkStopSide(values.direction, values.entry_price, values.stop_loss, ctx);
  });
export type TradeEntryFormInput = z.input<typeof tradeEntrySchema>;
export type TradeEntryFormValues = z.output<typeof tradeEntrySchema>;

/** `POST /trades/{id}/open` (new in v2.0) — `direction` is already fixed
 * on the Trade being opened (not part of this request body), so
 * INV-TRADE-01 re-validation needs it supplied externally; built as a
 * factory rather than a static schema for that reason. */
export function buildOpenTradeSchema(direction: "long" | "short") {
  return z
    .object({
      entry_price: z.coerce.number({ message: "Enter an entry price." }),
      entered_at: z.string().min(1, "Enter the entry date."),
      scoring_profile: z.string().min(1, "Select a trade type."),
      stop_loss: z.coerce.number().optional(),
      take_profit: z.coerce.number().optional(),
    })
    .superRefine((values, ctx) => {
      checkStopSide(direction, values.entry_price, values.stop_loss, ctx);
    });
}
export type OpenTradeFormInput = z.input<ReturnType<typeof buildOpenTradeSchema>>;
export type OpenTradeFormValues = z.output<ReturnType<typeof buildOpenTradeSchema>>;

/** `PATCH /trades/{id}` — every field optional, re-validated as a whole
 * proposed state (`TRADEOS_FRONTEND_BLUEPRINT.md` §10's Trade Amendment
 * row: "re-checked against the *proposed full state*"). */
export const amendTradeSchema = z
  .object({
    market: z.string().min(1, "Enter a market.").max(20, "Max 20 characters.").optional(),
    direction: z.enum(["long", "short"]).optional(),
    entry_price: z.coerce.number().optional(),
    stop_loss: z.coerce.number().optional(),
    take_profit: z.coerce.number().optional(),
    size: z.coerce.number().min(0, "Size must be 0 or greater.").optional(),
    margin_used: z.coerce.number().optional(),
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
      checkStopSide(values.direction, values.entry_price, values.stop_loss, ctx);
    }
  });
export type AmendTradeFormInput = z.input<typeof amendTradeSchema>;
export type AmendTradeFormValues = z.output<typeof amendTradeSchema>;

/** `POST /trades/{id}/close` — INV-TRADE-02 (`result`/`exit_price`
 * required together) is satisfied structurally here: both are always
 * required fields of this schema, never independently optional. v2.0:
 * `realized_pnl`/`closed_at` are now trader-supplied, required fields —
 * never server-computed. */
export const closeTradeSchema = z.object({
  result: z.enum(RESULT_VALUES, { message: "Select a result." }),
  exit_price: z.coerce.number({ message: "Enter an exit price." }),
  realized_pnl: z.coerce.number({ message: "Enter the realized P&L." }),
  closed_at: z.string().min(1, "Enter the close date."),
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
