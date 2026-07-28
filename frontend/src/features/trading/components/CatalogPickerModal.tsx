import { useQuery } from "@tanstack/react-query";

import { Modal } from "../../../components/Modal";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { catalogEntryKeys, listCatalogEntries } from "../../../shared/catalogEntries";

export interface CatalogPickerModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  kind: string;
  title: string;
  excludeIds?: string[];
  onSelect: (catalogEntryId: string) => void;
  isSelecting?: boolean;
}

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.3's `CatalogPickerModal` — "select
 * from Catalogs (kind=mistake_tag) via a lightweight picker" (§6.7).
 * Generic over `kind` so any future catalog-scoped picker reuses it
 * unchanged, though Mistake tagging is its only consumer this sprint.
 */
export function CatalogPickerModal({
  open,
  onOpenChange,
  kind,
  title,
  excludeIds = [],
  onSelect,
  isSelecting = false,
}: CatalogPickerModalProps) {
  const { data: entries, isLoading } = useQuery({
    queryKey: catalogEntryKeys.list(kind),
    queryFn: () => listCatalogEntries(kind),
    staleTime: STABLE_DATA_STALE_TIME_MS,
    enabled: open,
  });

  const excludeSet = new Set(excludeIds);
  const selectable = (entries ?? []).filter((entry) => entry.is_active && !excludeSet.has(entry.id));

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={title}>
      {isLoading ? (
        <p className="text-sm text-text-secondary">Loading…</p>
      ) : selectable.length === 0 ? (
        <p className="text-sm text-text-secondary">Nothing available to add.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {selectable.map((entry) => (
            <li key={entry.id}>
              <button
                type="button"
                disabled={isSelecting}
                onClick={() => onSelect(entry.id)}
                className="w-full rounded px-3 py-2 text-left text-sm text-text-primary hover:bg-bg-overlay disabled:opacity-50"
              >
                {entry.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  );
}
