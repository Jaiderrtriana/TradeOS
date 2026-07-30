/**
 * Chart series colors — Sprint 6.2. The project's own Design System
 * (`src/design-system/tokens.css`) defines only `accent` and `danger` as
 * named colors (`TRADEOS_FRONTEND_BLUEPRINT.md` §14: "no colors, no
 * CSS" beyond consistency principles) -- neither this file nor any
 * component adds a new token there. `ROLLING_COLOR` reuses the existing
 * `--color-accent` CSS variable (the app's real interactive color,
 * already meaning "current/live" per Badge.tsx's own accent-tone
 * convention). `OVERALL_COLOR` is one additional, validated-not-guessed
 * hex, chosen only because no second categorical hue exists in the
 * Design System yet and Rolling-vs-Overall is a genuine two-series
 * comparison: paired against the accent color and confirmed
 * colorblind-safe (CVD ΔE 30.3, normal-vision ΔE 33.3, both well above
 * the dataviz skill's 8/15 floors) against the app's dark surface
 * (`#141418`) via `scripts/validate_palette.js`.
 */
export const ROLLING_COLOR = "rgb(var(--color-accent))";
export const OVERALL_COLOR = "#d95926";
