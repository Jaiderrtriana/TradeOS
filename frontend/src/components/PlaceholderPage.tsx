/**
 * Sprint 0.3's only page content: a routable placeholder, reused by every
 * confirmed frontend module (TRADEOS_FRONTEND_BLUEPRINT.md §3) — "no
 * feature logic yet" (TRADEOS_IMPLEMENTATION_MASTER_PLAN.md Sprint 0.3).
 * Real page content arrives with each module's own phase.
 */
export interface PlaceholderPageProps {
  title: string;
}

export function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
      <p className="mt-2 text-sm text-text-secondary">
        The real content for this module is not implemented yet.
      </p>
    </div>
  );
}
