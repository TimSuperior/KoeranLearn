export type AdminEntityKey =
  | "paths"
  | "courses"
  | "modules"
  | "lessons"
  | "lesson-blocks"
  | "vocabulary"
  | "grammar"
  | "scenarios"
  | "dialogues"
  | "dialogue-lines"
  | "exercises"
  | "exercise-options"
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

export type DashboardEntitySummary = {
  total: number;
  draft: number;
  published: number;
  archived: number;
  premium: number;
  ready_to_publish: number;
  blocked: number;
  warnings: number;
};

export type DashboardOverview = {
  total_items: number;
  draft_items: number;
  published_items: number;
  archived_items: number;
  premium_items: number;
  ready_to_publish: number;
  blocked_items: number;
  warning_items: number;
};

export type DashboardSummary = {
  entities: Record<string, number>;
  drafts: Record<string, number>;
  premium: Record<string, number>;
  by_entity: Record<string, DashboardEntitySummary>;
  overview: DashboardOverview;
  publish_queue_total: number;
  validation_issue_total: number;
  validation_warning_total: number;
  audio_health: Record<string, number>;
};

export type PublishQueueItem = {
  entity: string;
  entity_id: number;
  label: string;
  status?: string | null;
  updated_at?: string | null;
  ready_to_publish: boolean;
  error_count: number;
  warning_count: number;
  deep_link?: string | null;
  issues: ValidationIssue[];
};

export type PublishQueueResponse = {
  items: PublishQueueItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ValidationCenterItem = {
  entity: string;
  entity_id: number;
  label: string;
  status?: string | null;
  updated_at?: string | null;
  error_count: number;
  warning_count: number;
  deep_link?: string | null;
  issues: ValidationIssue[];
};

export type ValidationCenterResponse = {
  items: ValidationCenterItem[];
  total: number;
  limit: number;
  offset: number;
};

export type AuditTrailItem = {
  id: number;
  created_at: string;
  admin_user_id?: number | null;
  admin_email?: string | null;
  action: string;
  entity_type: string;
  entity_id?: number | null;
  request_id?: string | null;
  before?: Record<string, any> | null;
  after?: Record<string, any> | null;
};

export type AuditTrailResponse = {
  items: AuditTrailItem[];
  total: number;
  limit: number;
  offset: number;
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
