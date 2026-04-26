from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ContentEntity = Literal[
    "paths",
    "courses",
    "modules",
    "lessons",
    "lesson-blocks",
    "exercises",
    "exercise-options",
    "vocabulary",
    "grammar",
    "example-sentences",
    "scenarios",
    "dialogues",
    "dialogue-lines",
    "audio-assets",
    "tags",
    "localization",
    "premium-packs",
]

ContentStatus = Literal["draft", "published", "archived"]
AccessState = Literal["free", "premium", "hidden", "internal", "inherit"]
ImportConflictStrategy = Literal["skip", "overwrite", "create_new", "merge"]
ImportFormat = Literal["json", "csv"]


class AdminContentListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


AudioAssetHealthFilter = Literal["expiring_soon", "unpublished", "broken", "missing", "disabled"]


class AdminContentWriteRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    relation_ids: dict[str, list[int]] = Field(default_factory=dict)
    children: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class AdminBulkStatusRequest(BaseModel):
    entity: ContentEntity
    ids: list[int] = Field(default_factory=list)
    status: ContentStatus | None = None
    access_state: AccessState | None = None


class AdminReorderRequest(BaseModel):
    order: list[int] = Field(default_factory=list)


class ValidationIssue(BaseModel):
    level: Literal["error", "warning"]
    code: str
    field: str | None = None
    message: str


class ValidationResult(BaseModel):
    entity: str
    valid: bool
    issues: list[ValidationIssue] = Field(default_factory=list)
    checked_at: datetime


class PreviewResponse(BaseModel):
    entity: str
    entity_id: int
    viewer_access: Literal["free", "premium"] = "free"
    learner_visible: bool
    locked_for_viewer: bool
    deep_link: str | None = None
    data: dict[str, Any]


class ImportRequest(BaseModel):
    format: ImportFormat = "json"
    content: str
    dry_run: bool = True
    conflict_strategy: ImportConflictStrategy = "skip"


class ImportErrorItem(BaseModel):
    row: int | None = None
    identifier: str | None = None
    message: str


class ImportResult(BaseModel):
    entity: str
    format: ImportFormat
    dry_run: bool
    created: int = 0
    updated: int = 0
    skipped: int = 0
    merged: int = 0
    errors: list[ImportErrorItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preview_items: list[dict[str, Any]] = Field(default_factory=list)


class ExportResponse(BaseModel):
    entity: str
    format: ImportFormat
    filename: str
    mime_type: str
    content: str
    count: int


class RelationOption(BaseModel):
    id: int
    label: str
    slug: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ContentOptionsResponse(BaseModel):
    options: dict[str, list[RelationOption]]
