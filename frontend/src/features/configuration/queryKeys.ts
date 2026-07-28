/**
 * Query key factory — Architecture Readiness Review (before Sprint 4.4):
 * see `features/evaluation/queryKeys.ts`'s own docstring for why this
 * exists uniformly across features now, rather than inline array
 * literals.
 */
export const configurationKeys = {
  versions: () => ["configuration", "versions"] as const,
  weights: (versionId: string) => ["configuration", "versions", versionId, "weights"] as const,
};
