/**
 * Query key factory — every Playbook query key goes through here, never
 * an inline array literal (Architecture Readiness Review, applied
 * uniformly since before Sprint 4.4).
 */
export const playbookKeys = {
  list: (cursor?: string) => ["playbook", "setups", "list", cursor ?? "first"] as const,
  detail: (setupId: string) => ["playbook", "setups", "detail", setupId] as const,
};
