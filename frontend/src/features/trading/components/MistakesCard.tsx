import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError } from "../../../api/errors";
import { Badge } from "../../../components/Badge";
import { useErrorReporter } from "../../../components/ErrorContext";
import { STABLE_DATA_STALE_TIME_MS } from "../../../queryClient";
import { catalogEntryKeys, listCatalogEntries } from "../../../shared/catalogEntries";
import { listTradeMistakes, tagMistake } from "../api";
import { tradingKeys } from "../queryKeys";
import { CatalogPickerModal } from "./CatalogPickerModal";

const MISTAKE_TAG_KIND = "mistake_tag";

/**
 * `TRADEOS_FRONTEND_BLUEPRINT.md` §8.3's `MistakesCard`: "Badge × N
 * (attached tags)" + "'+ Add' → CatalogPickerModal (kind=mistake_tag)".
 * Reads via `GET /trades/{id}/mistakes` (Sprint 4.4, closed alongside
 * this UI — Trade Detail cannot show attached tags without it).
 */
export function MistakesCard({ tradeId }: { tradeId: string }) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [pickerOpen, setPickerOpen] = useState(false);

  const { data: mistakes } = useQuery({
    queryKey: tradingKeys.mistakes(tradeId),
    queryFn: () => listTradeMistakes(tradeId),
  });

  const { data: mistakeTagEntries } = useQuery({
    queryKey: catalogEntryKeys.list(MISTAKE_TAG_KIND),
    queryFn: () => listCatalogEntries(MISTAKE_TAG_KIND),
    staleTime: STABLE_DATA_STALE_TIME_MS,
  });

  const addMistake = useMutation({
    mutationFn: (catalogEntryId: string) => tagMistake(tradeId, { catalog_entry_id: catalogEntryId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: tradingKeys.mistakes(tradeId) });
      setPickerOpen(false);
    },
    onError: (error: ApiError) => reportError(error),
  });

  const nameByEntryId = new Map((mistakeTagEntries ?? []).map((entry) => [entry.id, entry.name]));
  const taggedIds = (mistakes ?? []).map((m) => m.catalog_entry_id);

  return (
    <div className="rounded border border-border bg-bg-surface p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">Mistakes</h2>
        <button type="button" onClick={() => setPickerOpen(true)} className="text-sm text-accent">
          + Add
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {taggedIds.length === 0 ? (
          <p className="text-sm text-text-secondary">No mistakes tagged.</p>
        ) : (
          taggedIds.map((id) => (
            <Badge key={id} label={nameByEntryId.get(id) ?? id} tone="muted" />
          ))
        )}
      </div>

      <CatalogPickerModal
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        kind={MISTAKE_TAG_KIND}
        title="Tag a Mistake"
        excludeIds={taggedIds}
        onSelect={(catalogEntryId) => addMistake.mutate(catalogEntryId)}
        isSelecting={addMistake.isPending}
      />
    </div>
  );
}
