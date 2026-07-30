import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { deletePlaybookSetupAttachment } from "../api";
import { playbookKeys } from "../queryKeys";
import type { PlaybookSetupAttachment } from "../types";
import { AddAttachmentModal } from "./AddAttachmentModal";

/**
 * `TRADEOS_DOMAIN_MODEL.md` §8.8: "example references (e.g.,
 * screenshots)" — part of a Setup's own documentation. Images use
 * native lazy-loading (`loading="lazy"`) per `TRADEOS_FRONTEND_
 * BLUEPRINT.md` §16's "Image Optimization" principle — no new
 * dependency, same restraint `TRADEOS_TECHNICAL_STACK.md` applies
 * everywhere else.
 */
export function AttachmentsCard({
  setupId,
  attachments,
}: {
  setupId: string;
  attachments: PlaybookSetupAttachment[];
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();
  const [addModalOpen, setAddModalOpen] = useState(false);

  const deleteAttachment = useMutation({
    mutationFn: (attachmentId: string) => deletePlaybookSetupAttachment(setupId, attachmentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: playbookKeys.detail(setupId) });
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <div>
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-text-primary">Attachments</h2>
        <button type="button" onClick={() => setAddModalOpen(true)} className="text-sm text-accent">
          + Add
        </button>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {attachments.length === 0 ? (
          <p className="text-sm text-text-secondary">No attachments yet.</p>
        ) : (
          attachments.map((attachment) => (
            <div
              key={attachment.id}
              className="flex flex-col gap-2 rounded border border-border bg-bg-surface p-2"
            >
              <img
                src={attachment.file_reference}
                alt={attachment.caption || "Setup example"}
                loading="lazy"
                className="aspect-video w-full rounded object-cover"
              />
              {attachment.caption && (
                <p className="text-xs text-text-secondary">{attachment.caption}</p>
              )}
              <button
                type="button"
                onClick={() => deleteAttachment.mutate(attachment.id)}
                disabled={deleteAttachment.isPending}
                className="text-xs text-danger disabled:opacity-50"
              >
                Remove
              </button>
            </div>
          ))
        )}
      </div>

      <AddAttachmentModal setupId={setupId} open={addModalOpen} onOpenChange={setAddModalOpen} />
    </div>
  );
}
