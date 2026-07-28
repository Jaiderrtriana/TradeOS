import type { ChecklistAnswers } from "./types";

/**
 * Query key factory — Architecture Readiness Review (before Sprint 4.4):
 * every query key in this feature goes through here, never an inline
 * array literal, so a typo can't silently create an uninvalidatable
 * duplicate cache entry once this feature (and the app) has far more
 * than one query in it.
 */
export const evaluationKeys = {
  preview: (profile: string, answers: ChecklistAnswers) =>
    ["evaluation", "preview", profile, answers] as const,
};
