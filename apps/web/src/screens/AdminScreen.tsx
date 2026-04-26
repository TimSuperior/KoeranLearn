import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Copy,
  Download,
  Eye,
  FileUp,
  Filter,
  Globe,
  Plus,
  RefreshCcw,
  Save,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  Upload
} from "lucide-react";
import { useEffect, useMemo, useState, type ChangeEvent } from "react";
import { ACCESS_FILTER_ENTITIES, CORE_ENTITIES, ENTITY_LABELS, HEALTH_FILTER_ENTITIES, LEVEL_FILTER_ENTITIES, ORDERABLE_ENTITIES, SORT_OPTIONS, SUPPORT_ENTITIES, TOPIC_FILTER_ENTITIES } from "../admin/config";
import { AudioPlayer } from "../components/ui";
import type {
  AdminEntityKey,
  AdminFilters,
  AdminRow,
  DashboardSummary,
  ImportResult,
  PreviewResponse,
  RelationOption,
  RelationOptionsMap,
  ValidationIssue,
  ValidationResult
} from "../admin/types";
import { blankBlock, blankDialogue, blankDialogueLine, blankEntity, blankExerciseOption, blankLessonAsset, deepClone, joinLines, joinTags, localized, moveItem, parseLines, parseTags, slugify, withOrder } from "../admin/utils";
import { api } from "../lib/api";

const STATUS_OPTIONS = ["draft", "published", "archived"];
const ACCESS_OPTIONS = ["free", "hidden", "internal", "inherit"] as const;
const ACCESS_FILTER_OPTIONS = ["free", "hidden", "internal", "premium", "inherit"] as const;
const EXERCISE_TYPES = [
  "multiple_choice",
  "fill_in_blank",
  "sentence_reorder",
  "match_pairs",
  "choose_particle",
  "choose_verb_ending",
  "translation_selection",
  "dialogue_continuation",
  "listen_and_choose",
  "listen_and_order",
  "listen_and_match",
  "true_false",
  "flashcard_review"
] as const;
const BLOCK_TYPES = ["explanation", "vocabulary", "grammar", "example_sentence", "exercise", "recap", "quiz", "scenario_link"] as const;

const defaultFilters: AdminFilters = {
  q: "",
  status_filter: "",
  access_filter: "",
  topic: "",
  level: "",
  health_filter: "",
  sort_by: "order_index",
  sort_dir: "asc"
};

type Mode = "content" | "io";

export function AdminScreen() {
  const [email, setEmail] = useState(localStorage.getItem("adminEmail") || "admin@example.com");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("adminAccessToken") || "");
  const [entity, setEntity] = useState<AdminEntityKey>("lessons");
  const [mode, setMode] = useState<Mode>("content");
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null);
  const [options, setOptions] = useState<RelationOptionsMap>({});
  const [filters, setFilters] = useState<AdminFilters>(defaultFilters);
  const [items, setItems] = useState<AdminRow[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [draft, setDraft] = useState<AdminRow | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [importEntity, setImportEntity] = useState<AdminEntityKey>("lessons");
  const [importFormat, setImportFormat] = useState<"json" | "csv">("json");
  const [importDryRun, setImportDryRun] = useState(true);
  const [importConflict, setImportConflict] = useState("skip");
  const [importContent, setImportContent] = useState("");
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const entityOptions = useMemo(() => [...CORE_ENTITIES, ...SUPPORT_ENTITIES], []);

  useEffect(() => {
    if (!dirty) return undefined;
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    if (!token) return;
    void refreshMeta();
  }, [token]);

  useEffect(() => {
    if (!token || mode !== "content") return;
    void refreshList();
  }, [token, entity, filters, mode]);

  async function refreshMeta() {
    const [dashboardData, optionData] = await Promise.all([api.adminDashboard(token), api.adminContentOptions(token)]);
    setDashboard(dashboardData);
    setOptions(optionData);
  }

  async function refreshList(preferredId?: number | null) {
    setLoading(true);
    try {
      const response = await api.adminContentList(token, entity, filters);
      setItems(response.items);
      const nextSelected = preferredId ?? selectedId;
      if (nextSelected && response.items.some((item) => item.id === nextSelected)) {
        return;
      }
      if (!isNew && response.items[0]?.id) {
        await openItem(response.items[0].id as number, false);
      } else if (!response.items.length) {
        setDraft(null);
        setSelectedId(null);
      }
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    const response = await api.adminLogin(email, password);
    localStorage.setItem("adminEmail", email);
    setToken(response.access_token);
    setMessage("Admin session ready.");
  }

  async function openItem(id: number, confirmDirty = true) {
    if (confirmDirty && dirty && !window.confirm("Discard unsaved changes?")) {
      return;
    }
    const detail = await api.adminContentDetail(token, entity, id);
    setSelectedId(id);
    setDraft(normalizeDraft(entity, detail));
    setValidation(null);
    setPreview(null);
    setDirty(false);
    setIsNew(false);
  }

  function switchEntity(nextEntity: AdminEntityKey) {
    if (dirty && !window.confirm("Discard unsaved changes?")) {
      return;
    }
    setEntity(nextEntity);
    setFilters({ ...defaultFilters, sort_by: SORT_OPTIONS[nextEntity][0]?.value || "order_index" });
    setSelectedIds([]);
    setSelectedId(null);
    setDraft(null);
    setValidation(null);
    setPreview(null);
    setDirty(false);
    setIsNew(false);
    setMode("content");
  }

  function createNewItem() {
    if (dirty && !window.confirm("Discard unsaved changes?")) {
      return;
    }
    setDraft(blankEntity(entity));
    setSelectedId(null);
    setValidation(null);
    setPreview(null);
    setDirty(false);
    setIsNew(true);
  }

  async function saveCurrent() {
    if (!draft) return;
    const payload = buildPayload(entity, draft);
    const saved = (isNew && !draft.id)
      ? await api.adminCreateContent(token, entity, payload)
      : await api.adminUpdateContent(token, entity, Number(draft.id), payload) as AdminRow;
    setDraft(normalizeDraft(entity, saved));
    setSelectedId(saved.id || null);
    setDirty(false);
    setIsNew(false);
    setMessage(`${ENTITY_LABELS[entity]} saved.`);
    await refreshMeta();
    await refreshList(saved.id || null);
  }

  async function duplicateCurrent() {
    if (!draft?.id) return;
    const cloned = await api.adminDuplicateContent(token, entity, draft.id);
    setMessage(`${ENTITY_LABELS[entity]} duplicated.`);
    await refreshMeta();
    await refreshList(cloned.id || null);
    if (cloned.id) await openItem(Number(cloned.id), false);
  }

  async function deleteCurrent() {
    if (!draft?.id || !window.confirm(`Delete this ${ENTITY_LABELS[entity].toLowerCase()}?`)) return;
    await api.adminDeleteContent(token, entity, draft.id);
    setMessage(`${ENTITY_LABELS[entity]} archived.`);
    setDraft(null);
    setSelectedId(null);
    setDirty(false);
    setIsNew(false);
    await refreshMeta();
    await refreshList();
  }

  async function validateCurrent() {
    if (!draft) return;
    const payload = buildPayload(entity, draft);
    const result = await api.adminValidateContent(token, entity, payload);
    setValidation(result);
    setMessage(result.valid ? "Validation passed." : "Validation returned issues.");
  }

  async function previewCurrent() {
    if (!draft?.id) {
      setMessage("Save the item before previewing.");
      return;
    }
    const result = await api.adminPreviewContent(token, entity, draft.id, "free");
    setPreview(result);
  }

  async function publishCurrent() {
    if (!draft) return;
    if (dirty) {
      await saveCurrent();
    }
    if (!draft.id && !selectedId) return;
    try {
      const result = await api.adminPublishContent(token, entity, Number(draft.id || selectedId));
      setDraft(normalizeDraft(entity, result));
      setDirty(false);
      setMessage(`${ENTITY_LABELS[entity]} published.`);
      await refreshMeta();
      await refreshList(result.id || null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Publish failed.");
      await validateCurrent();
    }
  }

  async function unpublishCurrent() {
    if (!draft?.id) return;
    const result = await api.adminUnpublishContent(token, entity, draft.id);
    setDraft(normalizeDraft(entity, result));
    setDirty(false);
    setMessage(`${ENTITY_LABELS[entity]} moved to draft.`);
    await refreshMeta();
    await refreshList(result.id || null);
  }

  async function runBulk(status?: string, access_state?: string) {
    if (!selectedIds.length) return;
    await api.adminBulkContentState(token, { entity, ids: selectedIds, status, access_state });
    setMessage(`Updated ${selectedIds.length} ${ENTITY_LABELS[entity].toLowerCase()} items.`);
    setSelectedIds([]);
    await refreshMeta();
    await refreshList(selectedId);
  }

  async function reorderVisible(from: number, to: number) {
    const ordered = moveItem(items, from, to);
    setItems(ordered);
    await api.adminReorderContent(token, entity, ordered.map((item) => Number(item.id)).filter(Boolean));
    setMessage(`${ENTITY_LABELS[entity]} order updated.`);
    await refreshList(selectedId);
  }

  async function exportCurrent(format: "json" | "csv") {
    const response = await api.adminExportContent(token, entity, format);
    downloadFile(response.filename, response.content, response.mime_type);
  }

  async function downloadTemplate(format: "json" | "csv") {
    const response = await api.adminTemplateContent(token, importEntity, format);
    downloadFile(response.filename, response.content, response.mime_type);
  }

  async function executeImport() {
    const result = await api.adminImportContent(token, importEntity, {
      format: importFormat,
      content: importContent,
      dry_run: importDryRun,
      conflict_strategy: importConflict
    });
    setImportResult(result);
    setMessage(importDryRun ? "Import dry-run complete." : "Import applied.");
    if (!importDryRun) {
      await refreshMeta();
      if (importEntity === entity && mode === "content") {
        await refreshList(selectedId);
      }
    }
  }

  function updateDraft(nextDraft: AdminRow) {
    setDraft(nextDraft);
    setDirty(true);
  }

  async function onImportFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportContent(await file.text());
  }

  return (
    <div className="space-y-4">
      {!token ? (
        <section className="rounded-app border border-line bg-white p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-app bg-leaf/10 text-leaf">
              <ShieldCheck size={20} />
            </div>
            <div>
              <h2 className="font-semibold">Admin login</h2>
              <p className="text-sm text-ink/60">Content operations require an admin session.</p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input className="h-11 rounded-app border border-line bg-panel px-3" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" />
            <input className="h-11 rounded-app border border-line bg-panel px-3" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" />
          </div>
          <button type="button" onClick={login} className="mt-4 h-11 rounded-app bg-leaf px-4 font-medium text-white">Login</button>
        </section>
      ) : null}

      {message ? <div className="rounded-app border border-line bg-white px-4 py-3 text-sm text-ink/75">{message}</div> : null}

      {dashboard ? <DashboardGrid dashboard={dashboard} /> : null}

      {token ? (
        <>
          <section className="flex flex-wrap gap-2">
            <button type="button" onClick={() => setMode("content")} className={`h-10 rounded-app px-4 text-sm ${mode === "content" ? "bg-leaf text-white" : "border border-line bg-white"}`}>
              Content
            </button>
            <button type="button" onClick={() => setMode("io")} className={`h-10 rounded-app px-4 text-sm ${mode === "io" ? "bg-leaf text-white" : "border border-line bg-white"}`}>
              Import / export
            </button>
            <button type="button" onClick={() => void refreshMeta()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-4 text-sm">
              <RefreshCcw size={16} />
              Refresh
            </button>
          </section>

          {mode === "io" ? (
            <ImportExportPanel
              entity={importEntity}
              format={importFormat}
              dryRun={importDryRun}
              conflict={importConflict}
              content={importContent}
              result={importResult}
              onEntityChange={setImportEntity}
              onFormatChange={setImportFormat}
              onDryRunChange={setImportDryRun}
              onConflictChange={setImportConflict}
              onContentChange={setImportContent}
              onImport={executeImport}
              onTemplateDownload={downloadTemplate}
              onFileChange={onImportFile}
            />
          ) : (
            <>
              <section className="flex flex-wrap gap-2">
                {CORE_ENTITIES.map((item) => (
                  <button key={item} type="button" onClick={() => switchEntity(item)} className={`h-10 rounded-app px-3 text-sm ${entity === item ? "bg-leaf text-white" : "border border-line bg-white"}`}>
                    {ENTITY_LABELS[item]}
                  </button>
                ))}
              </section>
              <section className="flex flex-wrap gap-2">
                {SUPPORT_ENTITIES.map((item) => (
                  <button key={item} type="button" onClick={() => switchEntity(item)} className={`h-9 rounded-app px-3 text-sm ${entity === item ? "bg-sky text-white" : "border border-line bg-white"}`}>
                    {ENTITY_LABELS[item]}
                  </button>
                ))}
              </section>

              <FilterBar entity={entity} filters={filters} onChange={setFilters} />

              <section className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_360px]">
                <div className="space-y-3">
                  <div className="rounded-app border border-line bg-white p-3">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div>
                        <h3 className="font-semibold">{ENTITY_LABELS[entity]}</h3>
                        <p className="text-xs text-ink/55">{items.length} visible</p>
                      </div>
                      <button type="button" onClick={createNewItem} className="flex h-10 items-center gap-2 rounded-app bg-leaf px-3 text-sm font-medium text-white">
                        <Plus size={16} />
                        New
                      </button>
                    </div>
                    <div className="mb-3 flex flex-wrap gap-2">
                      <button type="button" onClick={() => void runBulk("published", undefined)} className="rounded-app border border-line px-2 py-2 text-xs">Publish selected</button>
                      <button type="button" onClick={() => void runBulk("draft", undefined)} className="rounded-app border border-line px-2 py-2 text-xs">Draft selected</button>
                      <button type="button" onClick={() => void runBulk(undefined, "free")} className="rounded-app border border-line px-2 py-2 text-xs">Set free</button>
                      <button type="button" onClick={() => void runBulk(undefined, "hidden")} className="rounded-app border border-line px-2 py-2 text-xs">Hide selected</button>
                    </div>
                    <div className="mb-3 flex gap-2">
                      <button type="button" onClick={() => void exportCurrent("json")} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
                        <Download size={16} />
                        JSON
                      </button>
                      {entity === "vocabulary" || entity === "grammar" ? (
                        <button type="button" onClick={() => void exportCurrent("csv")} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
                          <Download size={16} />
                          CSV
                        </button>
                      ) : null}
                    </div>
                    <div className="max-h-[70vh] overflow-y-auto">
                      {loading ? <p className="text-sm text-ink/55">Loading…</p> : null}
                      {items.map((item, index) => (
                        <div key={String(item.id)} className={`mb-2 rounded-app border p-2 ${selectedId === item.id && !isNew ? "border-leaf bg-leaf/5" : "border-line bg-panel/40"}`}>
                          <div className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              checked={selectedIds.includes(Number(item.id))}
                              onChange={(event) => {
                                const id = Number(item.id);
                                setSelectedIds((current) => event.target.checked ? [...current, id] : current.filter((value) => value !== id));
                              }}
                            />
                            <button type="button" onClick={() => void openItem(Number(item.id))} className="min-w-0 flex-1 text-left">
                              <p className="truncate text-sm font-medium">{String(item.display_label || item.slug || item.key || item.id)}</p>
                              <div className="mt-1 flex flex-wrap gap-1">
                                <Badge tone="neutral">{String(item.status || "draft")}</Badge>
                                {item.resolved_access_state ? <Badge tone={item.resolved_access_state === "premium" ? "sun" : "neutral"}>{formatAccessState(item.resolved_access_state)}</Badge> : null}
                                {entity === "audio-assets" && item.health?.state ? <Badge tone={item.health.state === "broken" || item.health.state === "missing" ? "coral" : item.health.state === "disabled" ? "sun" : "leaf"}>{String(item.health.state)}</Badge> : null}
                              </div>
                            </button>
                            {ORDERABLE_ENTITIES.has(entity) ? (
                              <div className="flex flex-col gap-1">
                                <button type="button" disabled={index === 0} onClick={() => void reorderVisible(index, index - 1)} className="rounded-app border border-line bg-white p-1 disabled:opacity-40">
                                  <ArrowUp size={14} />
                                </button>
                                <button type="button" disabled={index === items.length - 1} onClick={() => void reorderVisible(index, index + 1)} className="rounded-app border border-line bg-white p-1 disabled:opacity-40">
                                  <ArrowDown size={14} />
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-app border border-line bg-white p-4">
                    <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <h3 className="font-semibold">{isNew ? `New ${ENTITY_LABELS[entity].slice(0, -1)}` : draft?.display_label || ENTITY_LABELS[entity]}</h3>
                        <p className="text-sm text-ink/55">{dirty ? "Unsaved changes" : "Saved state"}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => void validateCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
                          <CheckCircle2 size={16} />
                          Validate
                        </button>
                        <button type="button" onClick={() => void previewCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
                          <Eye size={16} />
                          Preview
                        </button>
                        <button type="button" onClick={() => void saveCurrent()} className="flex h-10 items-center gap-2 rounded-app bg-leaf px-3 text-sm font-medium text-white">
                          <Save size={16} />
                          Save
                        </button>
                      </div>
                    </div>

                    {draft ? (
                      <div className="space-y-4">
                        <div className="flex flex-wrap gap-2">
                          {!isNew ? (
                            <>
                              <button type="button" onClick={() => void duplicateCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
                                <Copy size={16} />
                                Duplicate
                              </button>
                              <button type="button" onClick={() => void publishCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
                                <Sparkles size={16} />
                                Publish
                              </button>
                              <button type="button" onClick={() => void unpublishCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
                                <RefreshCcw size={16} />
                                Draft
                              </button>
                              <button type="button" onClick={() => void deleteCurrent()} className="flex h-10 items-center gap-2 rounded-app border border-line bg-panel px-3 text-sm text-coral">
                                <Trash2 size={16} />
                                Archive
                              </button>
                            </>
                          ) : null}
                        </div>

                        <EntityEditor entity={entity} draft={draft} options={options} token={token} onChange={updateDraft} />
                      </div>
                    ) : (
                      <div className="rounded-app border border-line bg-panel p-6 text-center text-sm text-ink/55">Select an item or create a new one.</div>
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-app border border-line bg-white p-4">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div>
                        <h3 className="font-semibold">Learner preview</h3>
                        <p className="text-sm text-ink/55">Shows the current free learner view and flags legacy gated content.</p>
                      </div>
                      <Badge tone="leaf">Free curriculum</Badge>
                    </div>
                    {preview ? <PreviewPanel preview={preview} /> : <p className="text-sm text-ink/55">Preview a saved item to inspect learner-facing output.</p>}
                  </div>

                  <div className="rounded-app border border-line bg-white p-4">
                    <div className="mb-3">
                      <h3 className="font-semibold">Validation</h3>
                      <p className="text-sm text-ink/55">Publishing rules and warnings.</p>
                    </div>
                    {validation ? <ValidationPanel validation={validation} /> : <p className="text-sm text-ink/55">Run validation on the current draft.</p>}
                  </div>
                </div>
              </section>
            </>
          )}
        </>
      ) : null}
    </div>
  );
}

function normalizeDraft(entity: AdminEntityKey, row: AdminRow): AdminRow {
  const next = deepClone(row);
  if (entity === "lessons") {
    next.blocks = next.blocks || [];
    next.assets = next.assets || [];
    next.relation_ids = next.relation_ids || { related_vocabulary: [], related_grammar: [], related_scenarios: [] };
  }
  if (entity === "scenarios") {
    next.dialogues = next.dialogues || [];
    next.relation_ids = next.relation_ids || { related_vocabulary: [], related_grammar: [], related_lessons: [] };
  }
  if (entity === "dialogues") next.dialogue_lines = next.dialogue_lines || [];
  if (entity === "exercises") next.options = next.options || [];
  if (entity === "vocabulary" || entity === "grammar") next.relation_ids = next.relation_ids || { related_lessons: [], related_scenarios: [] };
  if (entity === "audio-assets") {
    next.label = next.label || localized("");
    next.transcript = next.transcript || localized("");
    next.metadata_json = next.metadata_json || {};
  }
  return next;
}

function buildPayload(entity: AdminEntityKey, draft: AdminRow) {
  const copy = sanitizeLegacyAudioDraft(entity, deepClone(draft));
  const relation_ids = copy.relation_ids || {};
  const children: Record<string, AdminRow[]> = {};

  if (entity === "lessons") children.blocks = withOrder((copy.blocks || []).map((block: AdminRow) => ({ ...block, payload: stripLegacyAudioPayload(block.payload as Record<string, unknown> | undefined) })));
  if (entity === "lessons") children.assets = (copy.assets || []).filter((asset: AdminRow) => !isLegacyAudioLessonAsset(asset));
  if (entity === "scenarios") children.dialogues = withOrder((copy.dialogues || []).map((dialogue: AdminRow) => ({ ...dialogue, dialogue_lines: withOrder((dialogue.dialogue_lines || []).map(stripLegacyAudioLine)) })));
  if (entity === "dialogues") children.dialogue_lines = withOrder((copy.dialogue_lines || []).map(stripLegacyAudioLine));
  if (entity === "exercises") children.options = withOrder(copy.options || []);

  delete copy.display_label;
  delete copy.meta;
  delete copy.children;
  delete copy.exercises;
  delete copy.exercise_ids;
  delete copy.blocks;
  delete copy.assets;
  delete copy.dialogues;
  delete copy.dialogue_lines;
  delete copy.options;
  delete copy.relation_ids;
  delete copy.lines;
  delete copy.health;
  delete copy.preview_url;
  delete copy.linked_entity;

  return { data: copy, relation_ids, children };
}

function sanitizeLegacyAudioDraft(entity: AdminEntityKey, draft: AdminRow): AdminRow {
  if (entity === "vocabulary") {
    delete draft.audio_asset_url;
  }
  if (entity === "exercises") {
    draft.payload = stripLegacyAudioPayload(draft.payload as Record<string, unknown> | undefined);
  }
  return draft;
}

function stripLegacyAudioPayload(payload: Record<string, unknown> | undefined) {
  const next = { ...(payload || {}) };
  delete next.audio_asset_url;
  delete next.audio_url;
  return next;
}

function stripLegacyAudioLine(line: AdminRow): AdminRow {
  const next = { ...line };
  delete next.audio_asset_url;
  return next;
}

function isLegacyAudioLessonAsset(asset: AdminRow): boolean {
  const assetType = String(asset.asset_type || "").toLowerCase();
  if (assetType.includes("audio")) return true;
  const url = String(asset.url || "").toLowerCase().split("?")[0].split("#")[0];
  return [".mp3", ".m4a", ".aac", ".wav", ".ogg", ".oga", ".webm"].some((extension) => url.endsWith(extension));
}

function DashboardGrid({ dashboard }: { dashboard: DashboardSummary }) {
  const visibleEntities = [...CORE_ENTITIES, ...SUPPORT_ENTITIES].filter((key) => key in dashboard.entities);
  return (
    <section className="grid grid-cols-2 gap-3 xl:grid-cols-6">
      {visibleEntities.map((key) => (
        <div key={key} className="rounded-app border border-line bg-white p-3">
          <p className="text-xs text-ink/55">{ENTITY_LABELS[key] || key}</p>
          <p className="text-xl font-semibold">{dashboard.entities[key]}</p>
          <div className="mt-2 flex gap-2 text-xs text-ink/55">
            <span>live {(dashboard.entities[key] || 0) - (dashboard.drafts[key] || 0)}</span>
            <span>draft {dashboard.drafts[key] || 0}</span>
            {(dashboard.premium[key] || 0) > 0 ? <span>legacy gated {dashboard.premium[key]}</span> : null}
          </div>
        </div>
      ))}
    </section>
  );
}

function FilterBar({ entity, filters, onChange }: { entity: AdminEntityKey; filters: AdminFilters; onChange: (next: AdminFilters) => void }) {
  return (
    <section className="rounded-app border border-line bg-white p-3">
      <div className="grid gap-3 md:grid-cols-7">
        <label className="md:col-span-2">
          <span className="mb-1 flex items-center gap-2 text-xs font-medium text-ink/55"><Search size={14} /> Search</span>
          <input className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.q} onChange={(event) => onChange({ ...filters, q: event.target.value })} />
        </label>
        <label>
          <span className="mb-1 flex items-center gap-2 text-xs font-medium text-ink/55"><Filter size={14} /> Status</span>
          <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.status_filter} onChange={(event) => onChange({ ...filters, status_filter: event.target.value })}>
            <option value="">All</option>
            {STATUS_OPTIONS.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          <span className="mb-1 text-xs font-medium text-ink/55">Access</span>
          <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.access_filter} onChange={(event) => onChange({ ...filters, access_filter: event.target.value })} disabled={!ACCESS_FILTER_ENTITIES.has(entity)}>
            <option value="">All</option>
            {ACCESS_FILTER_OPTIONS.map((item) => <option key={item} value={item}>{formatAccessState(item)}</option>)}
          </select>
        </label>
        <label>
          <span className="mb-1 text-xs font-medium text-ink/55">Topic</span>
          <input className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.topic} onChange={(event) => onChange({ ...filters, topic: event.target.value })} disabled={!TOPIC_FILTER_ENTITIES.has(entity)} />
        </label>
        <label>
          <span className="mb-1 text-xs font-medium text-ink/55">Level</span>
          <input className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.level} onChange={(event) => onChange({ ...filters, level: event.target.value })} disabled={!LEVEL_FILTER_ENTITIES.has(entity)} />
        </label>
        <label>
          <span className="mb-1 text-xs font-medium text-ink/55">Audio health</span>
          <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={filters.health_filter} onChange={(event) => onChange({ ...filters, health_filter: event.target.value })} disabled={!HEALTH_FILTER_ENTITIES.has(entity)}>
            <option value="">All</option>
            <option value="expiring_soon">Expiring soon</option>
            <option value="unpublished">Unpublished</option>
            <option value="broken">Broken</option>
            <option value="missing">Missing file</option>
            <option value="disabled">Disabled</option>
          </select>
        </label>
      </div>
    </section>
  );
}

function ImportExportPanel(props: {
  entity: AdminEntityKey;
  format: "json" | "csv";
  dryRun: boolean;
  conflict: string;
  content: string;
  result: ImportResult | null;
  onEntityChange: (value: AdminEntityKey) => void;
  onFormatChange: (value: "json" | "csv") => void;
  onDryRunChange: (value: boolean) => void;
  onConflictChange: (value: string) => void;
  onContentChange: (value: string) => void;
  onImport: () => void;
  onTemplateDownload: (format: "json" | "csv") => void;
  onFileChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  const { entity, format, dryRun, conflict, content, result, onEntityChange, onFormatChange, onDryRunChange, onConflictChange, onContentChange, onImport, onTemplateDownload, onFileChange } = props;
  return (
    <section className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="rounded-app border border-line bg-white p-4">
        <h3 className="font-semibold">Import / export center</h3>
        <p className="mt-1 text-sm text-ink/55">Content-aware JSON packages plus CSV for vocabulary and grammar.</p>
        <div className="mt-4 space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink/55">Entity</span>
            <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={entity} onChange={(event) => onEntityChange(event.target.value as AdminEntityKey)}>
              {[...CORE_ENTITIES, ...SUPPORT_ENTITIES].map((item) => <option key={item} value={item}>{ENTITY_LABELS[item]}</option>)}
            </select>
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink/55">Format</span>
            <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={format} onChange={(event) => onFormatChange(event.target.value as "json" | "csv")}>
              <option value="json">JSON</option>
              <option value="csv" disabled={entity !== "vocabulary" && entity !== "grammar"}>CSV</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={dryRun} onChange={(event) => onDryRunChange(event.target.checked)} />
            Dry run only
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-ink/55">Conflict strategy</span>
            <select className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm" value={conflict} onChange={(event) => onConflictChange(event.target.value)}>
              <option value="skip">Skip</option>
              <option value="overwrite">Overwrite</option>
              <option value="create_new">Create new</option>
              <option value="merge">Merge</option>
            </select>
          </label>
          <div className="grid gap-2 sm:grid-cols-2">
            <button type="button" onClick={() => onTemplateDownload(format)} className="flex h-10 items-center justify-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
              <Download size={16} />
              Template
            </button>
            <label className="flex h-10 cursor-pointer items-center justify-center gap-2 rounded-app border border-line bg-panel px-3 text-sm">
              <FileUp size={16} />
              Upload file
              <input type="file" accept={format === "json" ? ".json" : ".csv"} className="hidden" onChange={onFileChange} />
            </label>
          </div>
          <button type="button" onClick={onImport} className="flex h-11 w-full items-center justify-center gap-2 rounded-app bg-leaf px-4 text-sm font-medium text-white">
            <Upload size={16} />
            {dryRun ? "Validate import" : "Apply import"}
          </button>
        </div>
      </div>
      <div className="space-y-4">
        <div className="rounded-app border border-line bg-white p-4">
          <h3 className="mb-3 font-semibold">Content package</h3>
          <textarea className="min-h-[360px] w-full rounded-app border border-line bg-panel p-3 font-mono text-xs outline-none focus:border-leaf" value={content} onChange={(event) => onContentChange(event.target.value)} />
        </div>
        <div className="rounded-app border border-line bg-white p-4">
          <h3 className="mb-3 font-semibold">Import result</h3>
          {result ? (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
                <Stat label="Created" value={String(result.created)} />
                <Stat label="Updated" value={String(result.updated)} />
                <Stat label="Merged" value={String(result.merged)} />
                <Stat label="Skipped" value={String(result.skipped)} />
                <Stat label="Errors" value={String(result.errors.length)} />
              </div>
              {result.errors.length ? (
                <div className="space-y-2">
                  {result.errors.map((error, index) => (
                    <div key={`${error.identifier || "error"}-${index}`} className="rounded-app border border-coral/20 bg-coral/5 p-3 text-sm text-coral">
                      Row {error.row ?? "?"}: {error.message}
                    </div>
                  ))}
                </div>
              ) : <p className="text-ink/55">No row-level errors.</p>}
            </div>
          ) : (
            <p className="text-sm text-ink/55">Run a dry-run or import to see the report.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function PreviewPanel({ preview }: { preview: PreviewResponse }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Badge tone={preview.learner_visible ? "leaf" : "coral"}>{preview.learner_visible ? "Learner visible" : "Hidden from learners"}</Badge>
        <Badge tone={preview.locked_for_viewer ? "sun" : "neutral"}>{preview.locked_for_viewer ? "Needs free-access cleanup" : "Free learner view"}</Badge>
      </div>
      {preview.deep_link ? (
        <a href={preview.deep_link} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-sky">
          <Globe size={16} />
          Open learner deep link
        </a>
      ) : null}
      <pre className="max-h-[460px] overflow-auto rounded-app border border-line bg-panel p-3 text-xs text-ink/80">{JSON.stringify(preview.data, null, 2)}</pre>
    </div>
  );
}

function ValidationPanel({ validation }: { validation: ValidationResult }) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        {validation.valid ? <CheckCircle2 size={18} className="text-leaf" /> : <AlertTriangle size={18} className="text-coral" />}
        <p className="text-sm font-medium">{validation.valid ? "Ready to publish" : "Issues found"}</p>
      </div>
      {validation.issues.length ? validation.issues.map((issue, index) => <IssueCard key={`${issue.code}-${index}`} issue={issue} />) : <p className="text-sm text-ink/55">No issues.</p>}
    </div>
  );
}

function IssueCard({ issue }: { issue: ValidationIssue }) {
  return (
    <div className={`rounded-app border p-3 text-sm ${issue.level === "error" ? "border-coral/20 bg-coral/5 text-coral" : "border-sun/20 bg-sun/10 text-ink/75"}`}>
      <p className="font-medium">{issue.code}</p>
      <p className="mt-1">{issue.message}</p>
      {issue.field ? <p className="mt-1 text-xs opacity-75">{issue.field}</p> : null}
    </div>
  );
}

function EntityEditor({ entity, draft, options, token, onChange }: { entity: AdminEntityKey; draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  if (entity === "lessons") return <LessonEditor draft={draft} options={options} token={token} onChange={onChange} />;
  if (entity === "vocabulary") return <VocabularyEditor draft={draft} options={options} token={token} onChange={onChange} />;
  if (entity === "grammar") return <GrammarEditor draft={draft} options={options} onChange={onChange} />;
  if (entity === "scenarios") return <ScenarioEditor draft={draft} options={options} token={token} onChange={onChange} />;
  if (entity === "dialogues") return <DialogueEditor draft={draft} options={options} token={token} onChange={onChange} />;
  if (entity === "exercises") return <ExerciseEditor draft={draft} options={options} token={token} onChange={onChange} />;
  if (entity === "audio-assets") return <AudioAssetEditor draft={draft} options={options} token={token} onChange={onChange} />;
  return <GenericEditor entity={entity} draft={draft} options={options} onChange={onChange} />;
}

function LessonEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <SelectField label="Module" value={draft.module_id ?? ""} onChange={(value) => onChange({ ...draft, module_id: value ? Number(value) : null })} options={toSelectOptions(options.modules)} />
      </div>
      <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value, slug: draft.slug || slugify(value.en || value.ru || value.uz) })} />
      <LocalizedEditor label="Summary" value={draft.summary || localized("")} onChange={(value) => onChange({ ...draft, summary: value })} rows={2} />
      <TextListEditor label="Objectives" value={draft.objectives || []} onChange={(value) => onChange({ ...draft, objectives: value })} />
      <LocalizedEditor label="Explanation" value={draft.explanation || localized("")} onChange={(value) => onChange({ ...draft, explanation: value })} rows={4} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField label="Topic" value={String(draft.topic || "")} onChange={(value) => onChange({ ...draft, topic: value })} />
        <TextField label="Difficulty" value={String(draft.difficulty || "")} onChange={(value) => onChange({ ...draft, difficulty: value })} />
        <TextField label="Minutes" value={String(draft.estimated_minutes || 0)} onChange={(value) => onChange({ ...draft, estimated_minutes: Number(value || 0) })} />
      </div>
      <TagField label="Tags" value={draft.tags || []} onChange={(value) => onChange({ ...draft, tags: value })} />
      <RelationPicker label="Related vocabulary" options={options.vocabulary || []} selected={draft.relation_ids?.related_vocabulary || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_vocabulary: value } })} />
      <RelationPicker label="Related grammar" options={options.grammar || []} selected={draft.relation_ids?.related_grammar || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_grammar: value } })} />
      <RelationPicker label="Related scenarios" options={options.scenarios || []} selected={draft.relation_ids?.related_scenarios || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_scenarios: value } })} />
      <RelationPicker label="Prerequisites" options={options.lessons || []} selected={draft.prerequisite_lesson_ids || []} onChange={(value) => onChange({ ...draft, prerequisite_lesson_ids: value })} />
      <LessonAssetsEditor assets={draft.assets || []} token={token} onChange={(assets) => onChange({ ...draft, assets })} />
      <BlocksEditor draft={draft} options={options} token={token} onChange={onChange} />
    </div>
  );
}

function VocabularyEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <TextField label="Korean" value={String(draft.korean || "")} onChange={(value) => onChange({ ...draft, korean: value, slug: draft.slug || slugify(value) })} />
      </div>
      <TextField label="Reading" value={String(draft.reading || "")} onChange={(value) => onChange({ ...draft, reading: value })} />
      <LocalizedEditor label="Translations" value={draft.translations || localized("")} onChange={(value) => onChange({ ...draft, translations: value })} rows={2} />
      <LocalizedEditor label="Usage notes" value={draft.usage_notes || localized("")} onChange={(value) => onChange({ ...draft, usage_notes: value })} rows={2} />
      <LocalizedEditor label="Notes" value={draft.notes || localized("")} onChange={(value) => onChange({ ...draft, notes: value })} rows={2} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField label="Topic" value={String(draft.topic || "")} onChange={(value) => onChange({ ...draft, topic: value })} />
        <TextField label="Difficulty" value={String(draft.difficulty || "")} onChange={(value) => onChange({ ...draft, difficulty: value })} />
        <TextField label="Part of speech" value={String(draft.politeness_level || "")} onChange={(value) => onChange({ ...draft, politeness_level: value })} />
      </div>
      <PremiumAudioAdminNote subject="vocabulary pronunciation and example audio" />
      <TagField label="Tags" value={draft.tags || []} onChange={(value) => onChange({ ...draft, tags: value })} />
      <TextListEditor label="Variants / synonyms" value={draft.variants || []} onChange={(value) => onChange({ ...draft, variants: value })} />
      <StructuredExamplesEditor value={draft.example_sentences || []} onChange={(value) => onChange({ ...draft, example_sentences: value })} />
      <RelationPicker label="Related lessons" options={options.lessons || []} selected={draft.relation_ids?.related_lessons || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_lessons: value } })} />
      <RelationPicker label="Related scenarios" options={options.scenarios || []} selected={draft.relation_ids?.related_scenarios || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_scenarios: value } })} />
    </div>
  );
}

function GrammarEditor({ draft, options, onChange }: { draft: AdminRow; options: RelationOptionsMap; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <TextField label="Korean pattern" value={String(draft.korean_pattern || "")} onChange={(value) => onChange({ ...draft, korean_pattern: value, slug: draft.slug || slugify(value) })} />
      </div>
      <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value })} />
      <LocalizedEditor label="Explanation" value={draft.explanation || localized("")} onChange={(value) => onChange({ ...draft, explanation: value })} rows={4} />
      <LocalizedEditor label="Usage notes" value={draft.usage_notes || localized("")} onChange={(value) => onChange({ ...draft, usage_notes: value })} rows={3} />
      <LocalizedListDictionaryEditor label="Common mistakes" value={draft.common_errors || { ru: [], uz: [], en: [] }} onChange={(value) => onChange({ ...draft, common_errors: value })} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField label="Category" value={String(draft.category || "")} onChange={(value) => onChange({ ...draft, category: value })} />
        <TextField label="Difficulty" value={String(draft.difficulty || "")} onChange={(value) => onChange({ ...draft, difficulty: value })} />
        <TextField label="Politeness / register" value={String(draft.politeness_level || "")} onChange={(value) => onChange({ ...draft, politeness_level: value })} />
      </div>
      <TagField label="Tags" value={draft.tags || []} onChange={(value) => onChange({ ...draft, tags: value })} />
      <TextListEditor label="Natural alternatives" value={draft.natural_alternatives || []} onChange={(value) => onChange({ ...draft, natural_alternatives: value })} />
      <RelationPicker label="Related lessons" options={options.lessons || []} selected={draft.relation_ids?.related_lessons || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_lessons: value } })} />
      <RelationPicker label="Related scenarios" options={options.scenarios || []} selected={draft.relation_ids?.related_scenarios || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_scenarios: value } })} />
    </div>
  );
}

function ScenarioEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <TextField label="Topic" value={String(draft.topic || "")} onChange={(value) => onChange({ ...draft, topic: value })} />
      </div>
      <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value, slug: draft.slug || slugify(value.en || value.ru || value.uz) })} />
      <LocalizedEditor label="Description" value={draft.description || localized("")} onChange={(value) => onChange({ ...draft, description: value })} rows={3} />
      <div className="grid gap-3 md:grid-cols-3">
        <TextField label="Difficulty" value={String(draft.difficulty || "")} onChange={(value) => onChange({ ...draft, difficulty: value })} />
        <TextField label="Order" value={String(draft.order_index || 0)} onChange={(value) => onChange({ ...draft, order_index: Number(value || 0) })} />
        <TextField label="Audience" value={String(draft.audience_metadata?.audience || "")} onChange={(value) => onChange({ ...draft, audience_metadata: { ...draft.audience_metadata, audience: value } })} />
      </div>
      <TextListEditor label="Roles" value={draft.roles || []} onChange={(value) => onChange({ ...draft, roles: value })} />
      <TagField label="Tags" value={draft.tags || []} onChange={(value) => onChange({ ...draft, tags: value })} />
      <TextListEditor label="Context labels" value={draft.context_labels || []} onChange={(value) => onChange({ ...draft, context_labels: value })} />
      <RelationPicker label="Related vocabulary" options={options.vocabulary || []} selected={draft.relation_ids?.related_vocabulary || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_vocabulary: value } })} />
      <RelationPicker label="Related grammar" options={options.grammar || []} selected={draft.relation_ids?.related_grammar || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_grammar: value } })} />
      <RelationPicker label="Related lessons" options={options.lessons || []} selected={draft.relation_ids?.related_lessons || []} onChange={(value) => onChange({ ...draft, relation_ids: { ...draft.relation_ids, related_lessons: value } })} />
      <DialoguesEditor draft={draft} options={options} token={token} onChange={onChange} />
    </div>
  );
}

function DialogueEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} inheritAllowed />
      <div className="grid gap-3 md:grid-cols-2">
        <SelectField label="Scenario" value={draft.scenario_id ?? ""} onChange={(value) => onChange({ ...draft, scenario_id: value ? Number(value) : null })} options={toSelectOptions(options.scenarios)} />
        <TextField label="Politeness" value={String(draft.politeness_level || "")} onChange={(value) => onChange({ ...draft, politeness_level: value })} />
      </div>
      <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value })} />
      <LocalizedEditor label="Context" value={draft.context || localized("")} onChange={(value) => onChange({ ...draft, context: value })} rows={2} />
      <LocalizedEditor label="Explanation" value={draft.explanation || localized("")} onChange={(value) => onChange({ ...draft, explanation: value })} rows={3} />
      <JsonField label="Checks" value={draft.checks || []} onChange={(value) => onChange({ ...draft, checks: value })} />
      <DialogueLinesEditor lines={draft.dialogue_lines || []} token={token} onChange={(dialogue_lines) => onChange({ ...draft, dialogue_lines })} />
    </div>
  );
}

function ExerciseEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  return (
    <div className="space-y-4">
      <BasicGovernanceFields draft={draft} onChange={onChange} inheritAllowed />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <SelectField label="Exercise type" value={String(draft.exercise_type || "multiple_choice")} onChange={(value) => onChange({ ...draft, exercise_type: value, answer_validation: { strategy: defaultStrategy(value) } })} options={EXERCISE_TYPES.map((value) => ({ value, label: value.replaceAll("_", " ") }))} />
      </div>
      <LocalizedEditor label="Prompt" value={draft.prompt || localized("")} onChange={(value) => onChange({ ...draft, prompt: value })} rows={2} />
      <LocalizedEditor label="Instructions" value={draft.instructions || localized("")} onChange={(value) => onChange({ ...draft, instructions: value })} rows={2} />
      <LocalizedEditor label="Feedback / explanation" value={draft.explanation || localized("")} onChange={(value) => onChange({ ...draft, explanation: value })} rows={2} />
      <div className="grid gap-3 md:grid-cols-4">
        <SelectField label="Lesson" value={draft.lesson_id ?? ""} onChange={(value) => onChange({ ...draft, lesson_id: value ? Number(value) : null })} options={toSelectOptions(options.lessons)} />
        <SelectField label="Grammar" value={draft.grammar_point_id ?? ""} onChange={(value) => onChange({ ...draft, grammar_point_id: value ? Number(value) : null })} options={toSelectOptions(options.grammar)} />
        <SelectField label="Vocabulary" value={draft.vocabulary_id ?? ""} onChange={(value) => onChange({ ...draft, vocabulary_id: value ? Number(value) : null })} options={toSelectOptions(options.vocabulary)} />
        <TextField label="Difficulty" value={String(draft.difficulty || "")} onChange={(value) => onChange({ ...draft, difficulty: value })} />
      </div>
      <TextField label="Topic" value={String(draft.topic || "")} onChange={(value) => onChange({ ...draft, topic: value })} />
      <TagField label="Tags" value={draft.tags || []} onChange={(value) => onChange({ ...draft, tags: value })} />
      <PremiumAudioAdminNote subject="exercise listening prompts" />
      <ExerciseAnswerEditor draft={draft} onChange={onChange} />
    </div>
  );
}

function AudioAssetEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  function setParent(field: string, rawValue: string) {
    const value = rawValue ? Number(rawValue) : null;
    onChange({
      ...draft,
      lesson_id: null,
      lesson_block_id: null,
      exercise_id: null,
      vocabulary_id: null,
      example_sentence_id: null,
      dialogue_line_id: null,
      scenario_id: null,
      [field]: value
    });
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <TextField label="Public ID" value={String(draft.public_id || "")} onChange={() => undefined} disabled />
        <TextField label="Original filename" value={String(draft.original_filename || "")} onChange={() => undefined} disabled />
      </div>

      <AudioAssetUploadField
        token={token}
        draft={draft}
        onUploaded={(nextDraft) => onChange(normalizeDraft("audio-assets", nextDraft))}
      />

      <LocalizedEditor label="Label" value={draft.label || localized("")} onChange={(value) => onChange({ ...draft, label: value })} rows={2} />

      <div className="grid gap-3 md:grid-cols-4">
        <TextField label="Attachment role" value={String(draft.attachment_role || "general")} onChange={(value) => onChange({ ...draft, attachment_role: value })} />
        <TextField label="Variant" value={String(draft.variant || "default")} onChange={(value) => onChange({ ...draft, variant: value })} />
        <TextField label="Source language" value={String(draft.source_language || "")} onChange={(value) => onChange({ ...draft, source_language: value || null })} />
        <TextField label="Target language" value={String(draft.target_language || "")} onChange={(value) => onChange({ ...draft, target_language: value || null })} />
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <SelectField label="Status" value={String(draft.status || "draft")} onChange={(value) => onChange({ ...draft, status: value })} options={STATUS_OPTIONS.map((value) => ({ value, label: value }))} />
        <SelectField
          label="Compliance"
          value={String(draft.compliance_state || "active")}
          onChange={(value) => onChange({ ...draft, compliance_state: value })}
          options={[
            { value: "active", label: "active" },
            { value: "disabled", label: "disabled" },
            { value: "broken", label: "broken" }
          ]}
        />
        <SelectField
          label="Transcript mode"
          value={String(draft.transcript_mode || "toggle")}
          onChange={(value) => onChange({ ...draft, transcript_mode: value })}
          options={[
            { value: "toggle", label: "toggle" },
            { value: "always", label: "always visible" },
            { value: "after_complete", label: "after completion" }
          ]}
        />
        <TextField label="Order" value={String(draft.order_index || 0)} onChange={(value) => onChange({ ...draft, order_index: Number(value || 0) })} />
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={Boolean(draft.premium_only ?? true)} onChange={(event) => onChange({ ...draft, premium_only: event.target.checked })} />
        Premium-only audio
      </label>

      <LocalizedEditor label="Transcript" value={draft.transcript || localized("")} onChange={(value) => onChange({ ...draft, transcript: value })} rows={3} />
      <JsonField label="Metadata" value={draft.metadata_json || {}} onChange={(value) => onChange({ ...draft, metadata_json: value })} />

      <div className="grid gap-3 md:grid-cols-2">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink/55">Expires at</span>
          <input
            type="datetime-local"
            className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm outline-none focus:border-leaf"
            value={toDateTimeLocalValue(draft.expires_at)}
            onChange={(event) => onChange({ ...draft, expires_at: event.target.value ? new Date(event.target.value).toISOString() : null })}
          />
        </label>
        <TextField label="Storage backend" value={String(draft.storage_backend || "")} onChange={() => undefined} disabled />
      </div>

      <section className="rounded-app border border-line bg-panel/50 p-4">
        <h4 className="mb-3 font-semibold">Linked content</h4>
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField label="Lesson" value={draft.lesson_id ?? ""} onChange={(value) => setParent("lesson_id", value)} options={toSelectOptions(options.lessons)} />
          <SelectField label="Lesson block" value={draft.lesson_block_id ?? ""} onChange={(value) => setParent("lesson_block_id", value)} options={toSelectOptions(options["lesson-blocks"])} />
          <SelectField label="Exercise" value={draft.exercise_id ?? ""} onChange={(value) => setParent("exercise_id", value)} options={toSelectOptions(options.exercises)} />
          <SelectField label="Vocabulary" value={draft.vocabulary_id ?? ""} onChange={(value) => setParent("vocabulary_id", value)} options={toSelectOptions(options.vocabulary)} />
          <SelectField label="Example sentence" value={draft.example_sentence_id ?? ""} onChange={(value) => setParent("example_sentence_id", value)} options={toSelectOptions(options["example-sentences"])} />
          <SelectField label="Dialogue line" value={draft.dialogue_line_id ?? ""} onChange={(value) => setParent("dialogue_line_id", value)} options={toSelectOptions(options["dialogue-lines"])} />
          <SelectField label="Scenario" value={draft.scenario_id ?? ""} onChange={(value) => setParent("scenario_id", value)} options={toSelectOptions(options.scenarios)} />
        </div>
        {draft.linked_entity ? (
          <p className="mt-3 text-sm text-ink/60">
            Current link: {String(draft.linked_entity.entity || "")} #{String(draft.linked_entity.id || "")} {draft.linked_entity.label ? `• ${String(draft.linked_entity.label)}` : ""}
          </p>
        ) : null}
      </section>

      <section className="rounded-app border border-line bg-panel/50 p-4">
        <h4 className="mb-3 font-semibold">Asset health</h4>
        <div className="grid gap-3 md:grid-cols-2">
          <Stat label="State" value={String(draft.health?.state || "draft")} />
          <Stat label="Duration" value={draft.duration_seconds ? `${draft.duration_seconds}s` : "unknown"} />
          <Stat label="Size" value={draft.size_bytes ? `${Math.round(Number(draft.size_bytes) / 1024)} KB` : "unknown"} />
          <Stat label="Expires soon" value={draft.health?.expiring_soon ? "yes" : "no"} />
        </div>
        {draft.last_error ? <div className="mt-3 rounded-app border border-coral/20 bg-coral/5 p-3 text-sm text-coral">{String(draft.last_error)}</div> : null}
      </section>

      {draft.preview_url ? (
        <section className="rounded-app border border-line bg-panel/50 p-4">
          <h4 className="mb-3 font-semibold">Admin preview</h4>
          <AudioPlayer src={String(draft.preview_url)} label="Admin preview" />
        </section>
      ) : null}
    </div>
  );
}

function GenericEditor({ entity, draft, options, onChange }: { entity: AdminEntityKey; draft: AdminRow; options: RelationOptionsMap; onChange: (next: AdminRow) => void }) {
  if (entity === "paths" || entity === "courses" || entity === "modules") {
    return (
      <div className="space-y-4">
        <BasicGovernanceFields draft={draft} onChange={onChange} inheritAllowed />
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
          {entity === "courses" ? <SelectField label="Path" value={draft.path_id ?? ""} onChange={(value) => onChange({ ...draft, path_id: value ? Number(value) : null })} options={toSelectOptions(options.paths)} /> : null}
          {entity === "modules" ? <SelectField label="Course" value={draft.course_id ?? ""} onChange={(value) => onChange({ ...draft, course_id: value ? Number(value) : null })} options={toSelectOptions(options.courses)} /> : null}
          {entity === "paths" ? <TextField label="Target goal" value={String(draft.target_goal || "")} onChange={(value) => onChange({ ...draft, target_goal: value })} /> : null}
        </div>
        <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value })} />
        <LocalizedEditor label="Description" value={draft.description || localized("")} onChange={(value) => onChange({ ...draft, description: value })} rows={3} />
        <div className="grid gap-3 md:grid-cols-3">
          <TextField label="Level / difficulty" value={String(draft.level || draft.difficulty || "")} onChange={(value) => onChange({ ...draft, level: value, difficulty: value })} />
          <TextField label="Order" value={String(draft.order_index || 0)} onChange={(value) => onChange({ ...draft, order_index: Number(value || 0) })} />
          {entity === "modules" ? <TextField label="Minutes" value={String(draft.estimated_minutes || 0)} onChange={(value) => onChange({ ...draft, estimated_minutes: Number(value || 0) })} /> : null}
        </div>
      </div>
    );
  }

  if (entity === "tags") {
    return (
      <div className="space-y-4">
        <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
        <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value })} rows={2} />
        <LocalizedEditor label="Description" value={draft.description || localized("")} onChange={(value) => onChange({ ...draft, description: value })} rows={2} />
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="Category" value={String(draft.category || "")} onChange={(value) => onChange({ ...draft, category: value })} />
          <SelectField label="Status" value={String(draft.status || "draft")} onChange={(value) => onChange({ ...draft, status: value })} options={STATUS_OPTIONS.map((value) => ({ value, label: value }))} />
        </div>
      </div>
    );
  }

  if (entity === "example-sentences") {
    return (
      <div className="space-y-4">
        <BasicGovernanceFields draft={draft} onChange={onChange} />
        <TextAreaField label="Korean" value={String(draft.korean || "")} onChange={(value) => onChange({ ...draft, korean: value })} rows={2} />
        <LocalizedEditor label="Translations" value={draft.translations || localized("")} onChange={(value) => onChange({ ...draft, translations: value })} rows={2} />
        <LocalizedEditor label="Explanation" value={draft.explanation || localized("")} onChange={(value) => onChange({ ...draft, explanation: value })} rows={2} />
        <div className="grid gap-3 md:grid-cols-2">
          <SelectField label="Grammar point" value={draft.grammar_point_id ?? ""} onChange={(value) => onChange({ ...draft, grammar_point_id: value ? Number(value) : null })} options={toSelectOptions(options.grammar)} />
          <SelectField label="Vocabulary" value={draft.vocabulary_id ?? ""} onChange={(value) => onChange({ ...draft, vocabulary_id: value ? Number(value) : null })} options={toSelectOptions(options.vocabulary)} />
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <TextField label="Register" value={String(draft.register || "")} onChange={(value) => onChange({ ...draft, register: value })} />
          <TextField label="Politeness" value={String(draft.politeness_level || "")} onChange={(value) => onChange({ ...draft, politeness_level: value })} />
        </div>
        <TextListEditor label="Context labels" value={draft.context_labels || []} onChange={(value) => onChange({ ...draft, context_labels: value })} />
      </div>
    );
  }

  if (entity === "localization") {
    return (
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <TextField label="Namespace" value={String(draft.namespace || "")} onChange={(value) => onChange({ ...draft, namespace: value })} />
          <TextField label="Key" value={String(draft.key || "")} onChange={(value) => onChange({ ...draft, key: value })} />
          <SelectField label="Language" value={String(draft.language || "en")} onChange={(value) => onChange({ ...draft, language: value })} options={[{ value: "ru", label: "RU" }, { value: "uz", label: "UZ" }, { value: "en", label: "EN" }]} />
        </div>
        <TextAreaField label="Value" value={String(draft.value || "")} onChange={(value) => onChange({ ...draft, value })} rows={6} />
        <SelectField label="Status" value={String(draft.status || "draft")} onChange={(value) => onChange({ ...draft, status: value })} options={STATUS_OPTIONS.map((value) => ({ value, label: value }))} />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <TextField label="Slug" value={String(draft.slug || "")} onChange={(value) => onChange({ ...draft, slug: value })} />
      <LocalizedEditor label="Title" value={draft.title || localized("")} onChange={(value) => onChange({ ...draft, title: value })} />
      <LocalizedEditor label="Description" value={draft.description || localized("")} onChange={(value) => onChange({ ...draft, description: value })} rows={3} />
      <div className="grid gap-3 md:grid-cols-4">
        <TextField label="Price minor" value={String(draft.price_minor || 0)} onChange={(value) => onChange({ ...draft, price_minor: Number(value || 0) })} />
        <TextField label="Currency" value={String(draft.currency || "USD")} onChange={(value) => onChange({ ...draft, currency: value })} />
        <TextField label="Order" value={String(draft.order_index || 0)} onChange={(value) => onChange({ ...draft, order_index: Number(value || 0) })} />
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-ink/55">Active</span>
          <input type="checkbox" checked={Boolean(draft.is_active)} onChange={(event) => onChange({ ...draft, is_active: event.target.checked })} />
        </label>
      </div>
      <JsonField label="Content rules" value={draft.content_rules || {}} onChange={(value) => onChange({ ...draft, content_rules: value })} />
    </div>
  );
}

function BasicGovernanceFields({ draft, onChange, inheritAllowed = false }: { draft: AdminRow; onChange: (next: AdminRow) => void; inheritAllowed?: boolean }) {
  const accessOptions = accessSelectOptions(draft.access_state, inheritAllowed);
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <SelectField label="Status" value={String(draft.status || "draft")} onChange={(value) => onChange({ ...draft, status: value })} options={STATUS_OPTIONS.map((value) => ({ value, label: value }))} />
      <SelectField label="Access" value={String(draft.access_state || "free")} onChange={(value) => onChange({ ...draft, access_state: value })} options={accessOptions} />
      <TextField label="Resolved access" value={formatAccessState(draft.resolved_access_state || draft.access_state || "free")} onChange={() => undefined} disabled />
    </div>
  );
}

function LessonAssetsEditor({ assets, token, onChange }: { assets: AdminRow[]; token: string; onChange: (assets: AdminRow[]) => void }) {
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h4 className="font-semibold">Lesson support assets</h4>
          <p className="text-sm text-ink/55">Keep this list for non-audio support files. Premium listening tracks live in Audio Assets.</p>
        </div>
        <button type="button" onClick={() => onChange([...(assets || []), blankLessonAsset()])} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
          <Plus size={16} />
          Add asset
        </button>
      </div>
      <PremiumAudioAdminNote subject="lesson-level listening tracks" />
      <div className="space-y-3">
        {(assets || []).length ? assets.map((asset, index) => (
          <div key={`${asset.id || "new"}-${index}`} className="rounded-app border border-line bg-white p-3">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="font-medium">Asset {index + 1}</p>
                <p className="text-xs text-ink/55">Audio tracks are now protected premium assets and should not be stored here.</p>
              </div>
              <button type="button" onClick={() => onChange(assets.filter((_, itemIndex) => itemIndex !== index))} className="rounded-app border border-line bg-panel p-2 text-coral">
                <Trash2 size={14} />
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <TextField label="Asset type" value={String(asset.asset_type || "")} onChange={(value) => onChange(updateAt(assets, index, { ...asset, asset_type: value }))} />
              <TextField label="Asset URL" value={String(asset.url || "")} onChange={(value) => onChange(updateAt(assets, index, { ...asset, url: value }))} />
            </div>
            <JsonField label="Metadata" value={asset.metadata_json || {}} onChange={(value) => onChange(updateAt(assets, index, { ...asset, metadata_json: value }))} />
            {asset.url ? <a href={String(asset.url)} target="_blank" rel="noreferrer" className="mt-3 inline-flex text-xs text-sky">Open current file</a> : null}
          </div>
        )) : (
          <div className="rounded-app border border-line bg-white p-4 text-sm text-ink/55">No media attached yet.</div>
        )}
      </div>
    </section>
  );
}

function AudioAssetUploadField({ token, draft, onUploaded }: { token: string; draft: AdminRow; onUploaded: (row: AdminRow) => void }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  async function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setProgress(0);
    setError("");
    try {
      const uploaded = await api.adminUploadAudioAsset(
        token,
        file,
        { audioAssetId: draft.id ? Number(draft.id) : undefined, attachmentRole: String(draft.attachment_role || "general") },
        setProgress
      );
      onUploaded(uploaded);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Upload failed.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="font-semibold">Protected audio file</h4>
          <p className="text-sm text-ink/55">Upload or replace the private audio file behind this stable asset reference.</p>
        </div>
        <label className={`inline-flex h-10 cursor-pointer items-center gap-2 rounded-app border border-line bg-white px-3 text-sm ${uploading ? "opacity-60" : ""}`}>
          <Upload size={14} />
          {uploading ? "Uploading..." : draft.id ? "Replace file" : "Upload file"}
          <input type="file" accept="audio/*" className="hidden" disabled={uploading} onChange={onFileChange} />
        </label>
      </div>
      {uploading ? (
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between text-xs text-ink/55">
            <span>Upload progress</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-panel">
            <div className="h-full rounded-full bg-leaf" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : null}
      {error ? <div className="mt-3 rounded-app border border-coral/20 bg-coral/5 p-3 text-sm text-coral">{error}</div> : null}
    </section>
  );
}

function BlocksEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  const blocks = (draft.blocks || []) as AdminRow[];
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h4 className="font-semibold">Lesson blocks</h4>
          <p className="text-sm text-ink/55">Explanation, vocab, grammar, exercise, recap, quiz, and scenario links.</p>
        </div>
        <button type="button" onClick={() => onChange({ ...draft, blocks: [...blocks, { ...blankBlock(), order_index: blocks.length }] })} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
          <Plus size={16} />
          Add block
        </button>
      </div>
      <div className="space-y-3">
        {blocks.map((block, index) => (
          <div key={`${block.id || "new"}-${index}`} className="rounded-app border border-line bg-white p-3">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <SelectField label="Type" value={String(block.block_type || "explanation")} onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, block_type: value }) })} options={BLOCK_TYPES.map((value) => ({ value, label: value.replaceAll("_", " ") }))} compact />
              <div className="flex gap-2">
                <button type="button" disabled={index === 0} onClick={() => onChange({ ...draft, blocks: withOrder(moveItem(blocks, index, index - 1)) })} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowUp size={14} /></button>
                <button type="button" disabled={index === blocks.length - 1} onClick={() => onChange({ ...draft, blocks: withOrder(moveItem(blocks, index, index + 1)) })} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowDown size={14} /></button>
                <button type="button" onClick={() => onChange({ ...draft, blocks: blocks.filter((_, itemIndex) => itemIndex !== index) })} className="rounded-app border border-line bg-panel p-2 text-coral"><Trash2 size={14} /></button>
              </div>
            </div>
            <LocalizedEditor label="Title" value={block.title || localized("")} onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, title: value }) })} rows={2} />
            <LocalizedEditor label="Body" value={block.body || localized("")} onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, body: value }) })} rows={3} />
            {block.block_type === "scenario_link" ? (
              <SelectField
                label="Scenario"
                value={String(block.payload?.scenario_id || "")}
                onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, payload: { ...block.payload, scenario_id: value ? Number(value) : null } }) })}
                options={toSelectOptions(options.scenarios)}
              />
            ) : null}
            {block.block_type === "exercise" ? (
              <SelectField
                label="Exercise"
                value={String(block.payload?.exercise_id || "")}
                onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, payload: { ...block.payload, exercise_id: value ? Number(value) : null } }) })}
                options={toSelectOptions(options.exercises)}
              />
            ) : null}
            <PremiumAudioAdminNote subject="lesson block audio" compact />
            <JsonField label="Payload" value={block.payload || {}} onChange={(value) => onChange({ ...draft, blocks: updateAt(blocks, index, { ...block, payload: value }) })} />
          </div>
        ))}
      </div>
    </section>
  );
}

function DialoguesEditor({ draft, options, token, onChange }: { draft: AdminRow; options: RelationOptionsMap; token: string; onChange: (next: AdminRow) => void }) {
  const dialogues = (draft.dialogues || []) as AdminRow[];
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h4 className="font-semibold">Dialogues</h4>
          <p className="text-sm text-ink/55">Scenario dialogue flows with ordered lines and reveal controls.</p>
        </div>
        <button type="button" onClick={() => onChange({ ...draft, dialogues: [...dialogues, { ...blankDialogue(), order_index: dialogues.length }] })} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
          <Plus size={16} />
          Add dialogue
        </button>
      </div>
      <div className="space-y-3">
        {dialogues.map((dialogue, index) => (
          <div key={`${dialogue.id || "new"}-${index}`} className="rounded-app border border-line bg-white p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="font-medium">Dialogue {index + 1}</p>
              <div className="flex gap-2">
                <button type="button" disabled={index === 0} onClick={() => onChange({ ...draft, dialogues: withOrder(moveItem(dialogues, index, index - 1)) })} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowUp size={14} /></button>
                <button type="button" disabled={index === dialogues.length - 1} onClick={() => onChange({ ...draft, dialogues: withOrder(moveItem(dialogues, index, index + 1)) })} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowDown size={14} /></button>
                <button type="button" onClick={() => onChange({ ...draft, dialogues: dialogues.filter((_, itemIndex) => itemIndex !== index) })} className="rounded-app border border-line bg-panel p-2 text-coral"><Trash2 size={14} /></button>
              </div>
            </div>
            <LocalizedEditor label="Title" value={dialogue.title || localized("")} onChange={(value) => onChange({ ...draft, dialogues: updateAt(dialogues, index, { ...dialogue, title: value }) })} />
            <LocalizedEditor label="Context" value={dialogue.context || localized("")} onChange={(value) => onChange({ ...draft, dialogues: updateAt(dialogues, index, { ...dialogue, context: value }) })} rows={2} />
            <LocalizedEditor label="Explanation" value={dialogue.explanation || localized("")} onChange={(value) => onChange({ ...draft, dialogues: updateAt(dialogues, index, { ...dialogue, explanation: value }) })} rows={2} />
            <DialogueLinesEditor
              lines={dialogue.dialogue_lines || []}
              token={token}
              onChange={(dialogue_lines) => onChange({ ...draft, dialogues: updateAt(dialogues, index, { ...dialogue, dialogue_lines }) })}
            />
          </div>
        ))}
      </div>
    </section>
  );
}

function DialogueLinesEditor({ lines, token, onChange }: { lines: AdminRow[]; token: string; onChange: (lines: AdminRow[]) => void }) {
  return (
    <section className="rounded-app border border-line bg-panel/40 p-3">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="font-medium">Dialogue lines</p>
        <button type="button" onClick={() => onChange([...lines, { ...blankDialogueLine(), order_index: lines.length }])} className="flex h-9 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
          <Plus size={14} />
          Add line
        </button>
      </div>
      <div className="space-y-3">
        {lines.map((line, index) => (
          <div key={`${line.id || "new"}-${index}`} className="rounded-app border border-line bg-white p-3">
            <div className="mb-2 flex items-center justify-between gap-2">
              <p className="font-medium text-sm">Line {index + 1}</p>
              <div className="flex gap-2">
                <button type="button" disabled={index === 0} onClick={() => onChange(withOrder(moveItem(lines, index, index - 1)))} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowUp size={14} /></button>
                <button type="button" disabled={index === lines.length - 1} onClick={() => onChange(withOrder(moveItem(lines, index, index + 1)))} className="rounded-app border border-line bg-panel p-2 disabled:opacity-40"><ArrowDown size={14} /></button>
                <button type="button" onClick={() => onChange(lines.filter((_, itemIndex) => itemIndex !== index))} className="rounded-app border border-line bg-panel p-2 text-coral"><Trash2 size={14} /></button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <TextField label="Speaker" value={String(line.speaker || "")} onChange={(value) => onChange(updateAt(lines, index, { ...line, speaker: value }))} />
              <SelectField label="Reveal" value={String(line.reveal_mode || "toggle")} onChange={(value) => onChange(updateAt(lines, index, { ...line, reveal_mode: value }))} options={[{ value: "toggle", label: "Toggle" }, { value: "always", label: "Always" }, { value: "hidden", label: "Hidden" }]} />
              <label className="block">
                <span className="mb-1 block text-xs font-medium text-ink/55">Useful expression</span>
                <input type="checkbox" checked={Boolean(line.is_useful_expression)} onChange={(event) => onChange(updateAt(lines, index, { ...line, is_useful_expression: event.target.checked }))} />
              </label>
            </div>
            <TextAreaField label="Korean" value={String(line.korean || "")} onChange={(value) => onChange(updateAt(lines, index, { ...line, korean: value }))} rows={2} />
            <LocalizedEditor label="Translations" value={line.translations || localized("")} onChange={(value) => onChange(updateAt(lines, index, { ...line, translations: value }))} rows={2} />
            <LocalizedEditor label="Notes" value={line.notes || localized("")} onChange={(value) => onChange(updateAt(lines, index, { ...line, notes: value }))} rows={2} />
            <PremiumAudioAdminNote subject="dialogue line audio" compact />
            <TagField label="Highlighted expressions" value={line.highlighted_expressions || []} onChange={(value) => onChange(updateAt(lines, index, { ...line, highlighted_expressions: value }))} />
          </div>
        ))}
      </div>
    </section>
  );
}

function ExerciseAnswerEditor({ draft, onChange }: { draft: AdminRow; onChange: (next: AdminRow) => void }) {
  const type = String(draft.exercise_type || "multiple_choice");
  const options = (draft.options || []) as AdminRow[];
  const update = (partial: Partial<AdminRow>) => onChange({ ...draft, ...partial });

  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <h4 className="mb-3 font-semibold">Answer definition</h4>
      {["multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "dialogue_continuation", "listen_and_choose", "true_false"].includes(type) ? (
        <div className="space-y-3">
          {options.map((option, index) => (
            <div key={`${option.id || "new"}-${index}`} className="grid gap-3 rounded-app border border-line bg-white p-3 md:grid-cols-[1fr_1fr_auto_auto]">
              <TextField label="Value" value={String(option.value || "")} onChange={(value) => update({ options: updateAt(options, index, { ...option, value }) })} />
              <LocalizedEditor label="Label" value={option.label || localized("")} onChange={(value) => update({ options: updateAt(options, index, { ...option, label: value }) })} rows={2} compact />
              <label className="mt-5 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={Boolean(option.is_correct)} onChange={(event) => update({ options: updateAt(options, index, { ...option, is_correct: event.target.checked }) })} />
                Correct
              </label>
              <button type="button" onClick={() => update({ options: options.filter((_, itemIndex) => itemIndex !== index) })} className="mt-5 rounded-app border border-line bg-panel p-2 text-coral">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button type="button" onClick={() => update({ options: [...options, blankExerciseOption()] })} className="flex h-10 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
            <Plus size={16} />
            Add option
          </button>
          <TextField label="Correct value" value={String(draft.answer_key?.value || "")} onChange={(value) => update({ answer_key: { value }, answer_validation: { strategy: defaultStrategy(type) } })} />
        </div>
      ) : null}

      {["sentence_reorder", "listen_and_order"].includes(type) ? (
        <div className="space-y-3">
          <TextAreaField label="Tokens (comma separated)" value={Array.isArray(draft.payload?.tokens) ? draft.payload.tokens.join(", ") : ""} onChange={(value) => update({ payload: { ...draft.payload, tokens: parseTags(value) } })} rows={3} />
          <TextAreaField label="Correct order (comma separated)" value={Array.isArray(draft.answer_key?.value) ? draft.answer_key.value.join(", ") : ""} onChange={(value) => update({ answer_key: { value: parseTags(value) }, answer_validation: { strategy: "ordered_list" } })} rows={3} />
        </div>
      ) : null}

      {["match_pairs", "listen_and_match"].includes(type) ? (
        <div className="space-y-3">
          <TextAreaField
            label="Pairs (left=right per line)"
            value={pairsToText(draft.answer_key?.value)}
            onChange={(value) => update({ answer_key: { value: textToPairs(value) }, answer_validation: { strategy: "unordered_pairs" } })}
            rows={6}
          />
        </div>
      ) : null}

      {["fill_in_blank", "flashcard_review"].includes(type) ? (
        <TextField label="Correct answer" value={String(draft.answer_key?.value || "")} onChange={(value) => update({ answer_key: { value }, answer_validation: { strategy: type === "flashcard_review" ? "exact" : "contains" } })} />
      ) : null}
    </section>
  );
}

function StructuredExamplesEditor({ value, onChange }: { value: any[]; onChange: (value: any[]) => void }) {
  const examples = Array.isArray(value) ? value : [];
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h4 className="font-semibold">Example sentences</h4>
        <button type="button" onClick={() => onChange([...examples, { korean: "", translations: localized("") }])} className="flex h-9 items-center gap-2 rounded-app border border-line bg-white px-3 text-sm">
          <Plus size={14} />
          Add example
        </button>
      </div>
      <div className="space-y-3">
        {examples.map((example, index) => (
          <div key={`example-${index}`} className="rounded-app border border-line bg-white p-3">
            <div className="mb-2 flex justify-end">
              <button type="button" onClick={() => onChange(examples.filter((_, itemIndex) => itemIndex !== index))} className="rounded-app border border-line bg-panel p-2 text-coral"><Trash2 size={14} /></button>
            </div>
            <TextAreaField label="Korean" value={String(example.korean || "")} onChange={(next) => onChange(updateAt(examples, index, { ...example, korean: next }))} rows={2} />
            <LocalizedEditor label="Translations" value={example.translations || localized("")} onChange={(next) => onChange(updateAt(examples, index, { ...example, translations: next }))} rows={2} />
          </div>
        ))}
      </div>
    </section>
  );
}

function RelationPicker({ label, options, selected, onChange }: { label: string; options: RelationOption[]; selected: number[]; onChange: (value: number[]) => void }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => options.filter((option) => option.label.toLowerCase().includes(query.toLowerCase()) || String(option.slug || "").toLowerCase().includes(query.toLowerCase())).slice(0, 20), [options, query]);

  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h4 className="font-semibold">{label}</h4>
        <span className="text-xs text-ink/55">{selected.length} selected</span>
      </div>
      <input className="mb-3 h-10 w-full rounded-app border border-line bg-white px-3 text-sm" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search…" />
      {selected.length ? (
        <div className="mb-3 flex flex-wrap gap-2">
          {selected.map((id) => {
            const option = options.find((item) => item.id === id);
            return (
              <button key={id} type="button" onClick={() => onChange(selected.filter((value) => value !== id))} className="rounded-app border border-line bg-white px-2 py-1 text-xs">
                {option?.label || id} ×
              </button>
            );
          })}
        </div>
      ) : null}
      <div className="grid gap-2">
        {filtered.map((option) => {
          const checked = selected.includes(option.id);
          return (
            <label key={option.id} className="flex items-center gap-2 rounded-app border border-line bg-white px-3 py-2 text-sm">
              <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked ? [...selected, option.id] : selected.filter((value) => value !== option.id))} />
              <span className="truncate">{option.label}</span>
            </label>
          );
        })}
      </div>
    </section>
  );
}

function LocalizedEditor({ label, value, onChange, rows = 3, compact = false }: { label: string; value: Record<string, string>; onChange: (value: Record<string, string>) => void; rows?: number; compact?: boolean }) {
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <h4 className="mb-3 font-semibold">{label}</h4>
      <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : ""}`}>
        {(["ru", "uz", "en"] as const).map((language) => (
          <label key={language} className="block">
            <span className="mb-1 block text-xs font-medium uppercase text-ink/55">{language}</span>
            <textarea className="w-full rounded-app border border-line bg-white p-3 text-sm outline-none focus:border-leaf" rows={rows} value={String(value?.[language] || "")} onChange={(event) => onChange({ ...value, [language]: event.target.value })} />
          </label>
        ))}
      </div>
    </section>
  );
}

function LocalizedListDictionaryEditor({ label, value, onChange }: { label: string; value: Record<string, string[]>; onChange: (value: Record<string, string[]>) => void }) {
  return (
    <section className="rounded-app border border-line bg-panel/50 p-4">
      <h4 className="mb-3 font-semibold">{label}</h4>
      <div className="grid gap-3 md:grid-cols-3">
        {(["ru", "uz", "en"] as const).map((language) => (
          <label key={language} className="block">
            <span className="mb-1 block text-xs font-medium uppercase text-ink/55">{language}</span>
            <textarea className="w-full rounded-app border border-line bg-white p-3 text-sm outline-none focus:border-leaf" rows={4} value={joinLines(value?.[language] || [])} onChange={(event) => onChange({ ...value, [language]: parseLines(event.target.value) })} />
          </label>
        ))}
      </div>
    </section>
  );
}

function TextListEditor({ label, value, onChange }: { label: string; value: any[]; onChange: (value: string[]) => void }) {
  return <TextAreaField label={label} value={joinLines(value)} onChange={(next) => onChange(parseLines(next))} rows={4} />;
}

function TagField({ label, value, onChange }: { label: string; value: any[]; onChange: (value: string[]) => void }) {
  return <TextField label={label} value={joinTags(value)} onChange={(next) => onChange(parseTags(next))} />;
}

function JsonField({ label, value, onChange }: { label: string; value: any; onChange: (value: any) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink/55">{label}</span>
      <textarea
        className="min-h-[120px] w-full rounded-app border border-line bg-panel p-3 font-mono text-xs outline-none focus:border-leaf"
        value={JSON.stringify(value ?? {}, null, 2)}
        onChange={(event) => {
          try {
            onChange(JSON.parse(event.target.value));
          } catch {
            onChange(value ?? {});
          }
        }}
      />
    </label>
  );
}

function TextField({ label, value, onChange, disabled = false }: { label: string; value: string; onChange: (value: string) => void; disabled?: boolean }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink/55">{label}</span>
      <input className="h-10 w-full rounded-app border border-line bg-panel px-3 text-sm outline-none focus:border-leaf disabled:opacity-50" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function TextAreaField({ label, value, onChange, rows = 4 }: { label: string; value: string; onChange: (value: string) => void; rows?: number }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink/55">{label}</span>
      <textarea className="w-full rounded-app border border-line bg-panel p-3 text-sm outline-none focus:border-leaf" rows={rows} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, onChange, options, compact = false }: { label: string; value: string | number; onChange: (value: string) => void; options: Array<{ value: string; label: string }>; compact?: boolean }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-ink/55">{label}</span>
      <select className={`w-full rounded-app border border-line bg-panel px-3 text-sm outline-none focus:border-leaf ${compact ? "h-10" : "h-10"}`} value={String(value)} onChange={(event) => onChange(event.target.value)}>
        <option value="">None</option>
        {options.map((option) => <option key={`${option.value}-${option.label}`} value={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function Badge({ children, tone }: { children: string; tone: "neutral" | "sun" | "leaf" | "coral" }) {
  const classes = tone === "sun" ? "bg-sun/15 text-ink" : tone === "leaf" ? "bg-leaf/15 text-leaf" : tone === "coral" ? "bg-coral/10 text-coral" : "bg-white text-ink/70";
  return <span className={`rounded-app border border-line px-2 py-1 text-[11px] ${classes}`}>{children}</span>;
}

function PremiumAudioAdminNote({ subject, compact = false }: { subject: string; compact?: boolean }) {
  return (
    <div className={`rounded-app border border-amber-500/20 bg-amber-500/5 text-sm text-ink/70 ${compact ? "p-3" : "p-4"}`}>
      Premium audio for {subject} is managed in <strong>Audio Assets</strong>. Attach protected tracks there and link them to this content instead of saving raw audio URLs here.
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-app border border-line bg-panel p-3">
      <p className="text-xs text-ink/55">{label}</p>
      <p className="text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatAccessState(value: string | null | undefined) {
  if (value === "premium") return "legacy-premium";
  return String(value || "free");
}

function accessSelectOptions(currentValue: string | null | undefined, inheritAllowed: boolean) {
  const base = inheritAllowed ? [...ACCESS_OPTIONS] : ACCESS_OPTIONS.filter((item) => item !== "inherit");
  const current = currentValue ? String(currentValue) : "";
  if (current && !base.includes(current as (typeof ACCESS_OPTIONS)[number])) {
    return [{ value: current, label: formatAccessState(current) }, ...base.map((value) => ({ value, label: formatAccessState(value) }))];
  }
  return base.map((value) => ({ value, label: formatAccessState(value) }));
}

function toSelectOptions(options: RelationOption[] | undefined) {
  return (options || []).map((option) => ({ value: String(option.id), label: option.label }));
}

function updateAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, itemIndex) => itemIndex === index ? value : item);
}

function defaultStrategy(exerciseType: string) {
  if (["multiple_choice", "choose_particle", "choose_verb_ending", "translation_selection", "dialogue_continuation", "listen_and_choose", "true_false"].includes(exerciseType)) return "one_of";
  if (["sentence_reorder", "listen_and_order"].includes(exerciseType)) return "ordered_list";
  if (["match_pairs", "listen_and_match"].includes(exerciseType)) return "unordered_pairs";
  if (exerciseType === "fill_in_blank") return "contains";
  return "exact";
}

function pairsToText(value: unknown) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return Object.entries(value as Record<string, unknown>).map(([left, right]) => `${left}=${String(right)}`).join("\n");
  }
  return "";
}

function textToPairs(value: string) {
  return Object.fromEntries(
    value
      .split("\n")
      .map((line) => line.split("=").map((item) => item.trim()))
      .filter((pair) => pair.length === 2 && pair[0] && pair[1]) as Array<[string, string]>
  );
}

function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function toDateTimeLocalValue(value: unknown) {
  if (!value) return "";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}
