import type { Config } from "tailwindcss";

// TRADEOS_TECHNICAL_STACK.md §6.13: theme is `preferences.theme`-driven via
// Tailwind's class-based dark mode strategy. Sprint 0.3 ships dark as the
// only theme (TRADEOS_FRONTEND_BLUEPRINT.md §14) — the `class` strategy
// itself is what lets a future light theme be additive later, per that
// same section.
const withOpacity = (variable: string) => `rgb(var(${variable}) / <alpha-value>)`;

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "bg-base": withOpacity("--color-bg-base"),
        "bg-surface": withOpacity("--color-bg-surface"),
        "bg-overlay": withOpacity("--color-bg-overlay"),
        "text-primary": withOpacity("--color-text-primary"),
        "text-secondary": withOpacity("--color-text-secondary"),
        "text-muted": withOpacity("--color-text-muted"),
        border: withOpacity("--color-border"),
        accent: withOpacity("--color-accent"),
        danger: withOpacity("--color-danger"),
      },
      fontFamily: {
        // §14: "monospace-for-numeric-data — Trade prices and R-multiples
        // benefit from tabular/monospace figures for scannability."
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
