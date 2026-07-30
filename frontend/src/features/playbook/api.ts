import { apiRequest } from "../../api/client";
import type {
  AddPlaybookSetupAttachmentPayload,
  CreatePlaybookSetupPayload,
  PaginatedPlaybookSetups,
  PlaybookSetupAttachment,
  PlaybookSetupDetail,
  PlaybookSetupSummary,
  UpdatePlaybookSetupPayload,
} from "./types";

/**
 * Playbook API wrappers — TRADEOS_API_SPECIFICATION.md §6.8, every
 * endpoint shipped in Sprint 7.1 (verified against
 * backend/app/modules/playbook/presentation/router.py). No
 * `DELETE /playbook-setups/{id}` — not in the confirmed contract.
 */

export function createPlaybookSetup(
  payload: CreatePlaybookSetupPayload,
): Promise<PlaybookSetupSummary> {
  return apiRequest<PlaybookSetupSummary>("/playbook-setups", { method: "POST", body: payload });
}

export function listPlaybookSetups(cursor?: string): Promise<PaginatedPlaybookSetups> {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return apiRequest<PaginatedPlaybookSetups>(`/playbook-setups${query}`);
}

export function getPlaybookSetup(setupId: string): Promise<PlaybookSetupDetail> {
  return apiRequest<PlaybookSetupDetail>(`/playbook-setups/${setupId}`);
}

export function updatePlaybookSetup(
  setupId: string,
  payload: UpdatePlaybookSetupPayload,
): Promise<PlaybookSetupSummary> {
  return apiRequest<PlaybookSetupSummary>(`/playbook-setups/${setupId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deprecatePlaybookSetup(setupId: string): Promise<PlaybookSetupSummary> {
  return apiRequest<PlaybookSetupSummary>(`/playbook-setups/${setupId}/deprecate`, {
    method: "POST",
  });
}

export function addPlaybookSetupAttachment(
  setupId: string,
  payload: AddPlaybookSetupAttachmentPayload,
): Promise<PlaybookSetupAttachment> {
  return apiRequest<PlaybookSetupAttachment>(`/playbook-setups/${setupId}/attachments`, {
    method: "POST",
    body: payload,
  });
}

export function deletePlaybookSetupAttachment(
  setupId: string,
  attachmentId: string,
): Promise<void> {
  return apiRequest<void>(`/playbook-setups/${setupId}/attachments/${attachmentId}`, {
    method: "DELETE",
  });
}
