export type AdminEntityKey =
  | "paths"
  | "courses"
  | "modules"
  | "lessons"
  | "vocabulary"
  | "grammar"
  | "scenarios"
  | "dialogues"
  | "exercises"
  | "audio-assets"
  | "example-sentences"
  | "tags"
  | "localization"
  | "premium-packs";

export type LocalizedText = {
  ru: string;
  uz: string;
  en: string;
};

export type AdminRow = Record<string, any> & {
  id?: number;
  slug?: string;
  display_label?: string;
  status?: string;
  access_state?: string;
  resolved_access_state?: string;
  relation_ids?: Record<string, number[]>;
  children?: Record<string, AdminRow[]>;
};

export type RelationOption = {
  id: number;
  label: string;
  slug?: string | null;
  meta: Record<string, any>;
};

export type RelationOptionsMap = Record<string, RelationOption[]>;

export type ValidationIssue = {
  level: "error" | "warning";
  code: string;
  field?: string | null;
  message: string;
};

export type ValidationResult = {
  entity: string;
  valid: boolean;
  issues: ValidationIssue[];
  checked_at: string;
};

export type PreviewResponse = {
  entity: string;
  entity_id: number;
  viewer_access: "free" | "premium";
  learner_visible: boolean;
  locked_for_viewer: boolean;
  deep_link?: string | null;
  data: Record<string, any>;
};

export type ImportResult = {
  entity: string;
  format: "json" | "csv";
  dry_run: boolean;
  created: number;
  updated: number;
  skipped: number;
  merged: number;
  errors: Array<{ row?: number | null; identifier?: string | null; message: string }>;
  warnings: string[];
  preview_items: Record<string, any>[];
};

export type ExportResponse = {
  entity: string;
  format: "json" | "csv";
  filename: string;
  mime_type: string;
  content: string;
  count: number;
};

export type AdminListResponse = {
  items: AdminRow[];
  total: number;
  limit: number;
  offset: number;
};

export type DashboardSummary = {
  entities: Record<string, number>;
  drafts: Record<string, number>;
  premium: Record<string, number>;
};

export type AdminFilters = {
  q: string;
  status_filter: string;
  access_filter: string;
  topic: string;
  level: string;
  health_filter: string;
  sort_by: string;
  sort_dir: "asc" | "desc";
};
