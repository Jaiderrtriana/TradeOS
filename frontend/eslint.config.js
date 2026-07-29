import js from "@eslint/js";
import boundaries from "eslint-plugin-boundaries";
import eslintConfigPrettier from "eslint-config-prettier";
import jsxA11y from "eslint-plugin-jsx-a11y";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

// TRADEOS_TECHNICAL_STACK.md §11.3: ESLint (with eslint-plugin-jsx-a11y
// for accessibility) + Prettier.
export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      react,
      "react-hooks": reactHooks,
      "jsx-a11y": jsxA11y,
      boundaries,
    },
    languageOptions: {
      ecmaVersion: 2022,
      globals: {
        window: "readonly",
        document: "readonly",
      },
    },
    settings: {
      react: { version: "18.3" },
      // `boundaries/dependencies` resolves import specifiers via
      // `eslint-module-utils/resolve`, which needs an `import/resolver`
      // to handle extension-less TS imports (e.g. `"../auth/tokenStorage"`).
      // Without this, every relative import fails to resolve, every
      // dependency's "to" element comes back unknown, and the rule
      // silently skips it — the exact false-negative diagnosed while
      // debugging this config (confirmed via `ESLINT_PLUGIN_BOUNDARIES_DEBUG=1`).
      "import/resolver": {
        typescript: { project: "./tsconfig.app.json" },
      },
      // Feature-boundary enforcement — Architecture Readiness Review
      // (before Sprint 4.4): `TRADEOS_FRONTEND_BLUEPRINT.md` §2.4 ("Cross
      // -feature reuse goes through Section 7's shared component library,
      // never through one feature importing another feature's internals
      // directly") was, until now, a convention documented in comments
      // only — nothing failed a build if a future feature violated it.
      // With 9 features today this held by discipline alone; the audit's
      // own "80+ pages, 150+ components" scale test is exactly where
      // that discipline stops being reliable on its own.
      "boundaries/elements": [
        // Pages are this architecture's own composition points — the
        // Frontend Blueprint's own wireframes have a page assembling
        // cards from multiple Bounded Contexts onto one screen (e.g.
        // TradeDetailPage hosting TradeSummaryCard/EvaluationSummaryCard
        // (Trading), MistakesCard (Trading's own mistakes endpoints),
        // and JournalEntriesCard (a genuinely separate `journal`
        // feature) — Sprint 5.1). Matched *before* the broader `feature`
        // pattern below so a `pages/*` file gets this permissive
        // treatment instead, mirroring the composition-root exception's
        // own stated rationale ("legitimately need to import from every
        // feature to wire the app together") applied one level down, to
        // a single page rather than the whole app. Everything else in a
        // feature (components/, api.ts, types.ts, hooks/) stays strictly
        // isolated — only `pages/` gets this.
        { type: "page", pattern: "src/features/*/pages", capture: ["feature"] },
        { type: "feature", pattern: "src/features/*", capture: ["feature"] },
        { type: "shared", pattern: "src/shared" },
        { type: "component", pattern: "src/components" },
        { type: "api", pattern: "src/api" },
        { type: "auth", pattern: "src/auth" },
        { type: "layout", pattern: "src/layout" },
        // The composition root (App.tsx, router.tsx, main.tsx,
        // queryClient.ts) is deliberately *not* a classified element:
        // `eslint-plugin-boundaries` only matches folders, not individual
        // top-level files (its own diagnostic confirms this), and these
        // four files legitimately need to import from every feature to
        // wire the app together — leaving them unmatched means the
        // dependency rule below simply never applies to them, which is
        // the correct, lenient behavior for a composition root.
      ],
    },
    rules: {
      ...react.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      ...jsxA11y.configs.recommended.rules,
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off",
      // A feature may import its own files freely, plus `shared`/
      // `components`/`api`/`auth`/`layout` — never another feature's
      // internals (that is what `shared`/`components` exist for).
      "boundaries/dependencies": [
        "error",
        {
          default: "disallow",
          policies: [
            {
              // Pages compose freely across every feature and shared
              // layer — see the `page` element's own comment above.
              from: { element: { type: "page" } },
              allow: {
                to: {
                  element: {
                    types: { anyOf: ["page", "feature", "shared", "component", "api", "auth", "layout"] },
                  },
                },
              },
            },
            {
              from: { element: { type: "feature" } },
              allow: {
                to: {
                  element: {
                    type: "feature",
                    captured: { feature: "{{from.element.captured.feature}}" },
                  },
                },
              },
            },
            {
              from: { element: { type: "feature" } },
              allow: {
                to: {
                  element: {
                    types: { anyOf: ["shared", "component", "api", "auth", "layout"] },
                  },
                },
              },
            },
            {
              from: { element: { type: "shared" } },
              allow: { to: { element: { types: { anyOf: ["shared", "api"] } } } },
            },
            {
              from: { element: { type: "component" } },
              allow: { to: { element: { types: { anyOf: ["component", "shared", "api"] } } } },
            },
            {
              // `src/api/client.ts` reads the access token from
              // `src/auth/tokenStorage.ts` to attach `Authorization`
              // (Sprint 1.2, already shipped) — a real, approved
              // dependency this policy must account for.
              from: { element: { type: "api" } },
              allow: { to: { element: { types: { anyOf: ["api", "auth"] } } } },
            },
            {
              from: { element: { type: "auth" } },
              allow: { to: { element: { types: { anyOf: ["auth", "api"] } } } },
            },
            {
              from: { element: { type: "layout" } },
              allow: {
                to: {
                  element: { types: { anyOf: ["layout", "shared", "component", "auth", "api"] } },
                },
              },
            },
          ],
        },
      ],
    },
  },
  eslintConfigPrettier,
);
