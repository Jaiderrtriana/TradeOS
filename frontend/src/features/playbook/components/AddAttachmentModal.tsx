import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";

import type { ApiError } from "../../../api/errors";
import { useErrorReporter } from "../../../components/ErrorContext";
import { Modal } from "../../../components/Modal";
import { addPlaybookSetupAttachment } from "../api";
import { playbookKeys } from "../queryKeys";
import {
  addPlaybookSetupAttachmentSchema,
  type AddPlaybookSetupAttachmentFormValues,
} from "../schemas";

/**
 * `POST /playbook-setups/{id}/attachments` — `file_reference` is a
 * caller-supplied URL/key to something already hosted elsewhere, never
 * a real file upload (Sprint 7.1's backend contract only ever persists a
 * string reference; no object-storage provider is chosen, Open Question
 * OQ-6). No native `<input type="file">`/`FormData` is used here — that
 * would imply a real upload path this system does not have.
 */
export function AddAttachmentModal({
  setupId,
  open,
  onOpenChange,
}: {
  setupId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const { reportError } = useErrorReporter();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AddPlaybookSetupAttachmentFormValues>({
    resolver: zodResolver(addPlaybookSetupAttachmentSchema),
    defaultValues: { file_reference: "", caption: "" },
  });

  const addAttachment = useMutation({
    mutationFn: (values: AddPlaybookSetupAttachmentFormValues) =>
      addPlaybookSetupAttachment(setupId, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: playbookKeys.detail(setupId) });
      reset();
      onOpenChange(false);
    },
    onError: (error: ApiError) => reportError(error),
  });

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Add Attachment"
      description="Paste a URL to an already-hosted image or example — this project does not upload files itself."
    >
      <form
        onSubmit={handleSubmit((values) => addAttachment.mutate(values))}
        className="flex flex-col gap-4"
      >
        <div>
          <label htmlFor="file_reference" className="mb-1 block text-sm text-text-secondary">
            File Reference (URL)
          </label>
          <input
            id="file_reference"
            type="text"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("file_reference")}
          />
          {errors.file_reference && (
            <p className="mt-1 text-xs text-danger">{errors.file_reference.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="caption" className="mb-1 block text-sm text-text-secondary">
            Caption
          </label>
          <input
            id="caption"
            type="text"
            className="w-full rounded border border-border bg-bg-base px-3 py-2 text-sm text-text-primary"
            {...register("caption")}
          />
        </div>

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="rounded border border-border px-3 py-2 text-sm text-text-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={addAttachment.isPending}
            className="rounded bg-accent px-3 py-2 text-sm font-medium text-text-primary disabled:opacity-50"
          >
            {addAttachment.isPending ? "Adding…" : "Add Attachment"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
