/**
 * Configuration & Catalogs types — mirrored field-for-field from the real
 * backend schemas (TRADEOS_API_SPECIFICATION.md §6.6-6.7, verified
 * directly against backend/app/modules/configuration/presentation/
 * schemas.py and catalog_schemas.py, Sprints 2.1-2.2). No field renamed,
 * added, or removed relative to the actual wire shape.
 *
 * `ScoringProfile`/`ScoringCriterion` are **not** redefined here —
 * imported from `src/shared/scoringReferenceData.ts` instead
 * (Architecture Readiness Review, before Sprint 4.4): see that module's
 * own docstring.
 */

export interface EngineType {
  code: string;
  display_name: string;
  is_signed: boolean;
  is_active: boolean;
}

export type ScoringConfigurationVersionStatus = "draft" | "published" | "superseded";

export interface ScoringConfigurationVersion {
  id: string;
  version_label: string;
  status: ScoringConfigurationVersionStatus;
  published_at: string | null;
  created_by_user_id: string | null;
  created_at: string;
}

export interface ScoringWeight {
  id: string;
  configuration_version_id: string;
  criterion_id: string;
  profile_code: string;
  weight: number;
  is_active: boolean;
}

export interface UpdateDraftWeightPayload {
  criterion_id: string;
  profile_code: string;
  weight: number;
  is_active?: boolean;
}

export type CatalogEntryKind = "setup" | "session" | "strategy" | "entry_trigger" | "mistake_tag";

export interface CatalogEntry {
  id: string;
  kind: string;
  name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
