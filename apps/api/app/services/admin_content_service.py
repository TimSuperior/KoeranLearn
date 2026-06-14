import csv
import io
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, inspect, or_
from sqlalchemy.orm import Session, selectinload

from app.admin_schemas import (
    AuditTrailItem,
    AuditTrailResponse,
    DashboardEntitySummary,
    DashboardOverview,
    DashboardSummary,
    ExportResponse,
    ImportRequest,
    ImportResult,
    PreviewResponse,
    PublishQueueItem,
    PublishQueueResponse,
    RelationOption,
    ValidationCenterItem,
    ValidationCenterResponse,
    ValidationIssue,
    ValidationResult,
)
from app.core.config import get_settings
from app.models.schema import (
    AdminAuditLog,
    AdminUser,
    AudioAsset,
    ContentTag,
    Course,
    Dialogue,
    DialogueLine,
    ExampleSentence,
    Exercise,
    ExerciseOption,
    GrammarPoint,
    LearningPath,
    Lesson,
    LessonAsset,
    LessonBlock,
    LocalizationEntry,
    Module,
    PremiumPack,
    Scenario,
    Vocabulary,
    utcnow,
)
from app.services.audio_service import ALLOWED_AUDIO_EXTENSIONS, admin_preview_url, audio_asset_admin_health
from app.services.content_access import locked_for_viewer, propagate_access_state, sync_access_state
from app.services.content_validation import ensure_publishable, validate_entity_payload


@dataclass(frozen=True)
class ChildConfig:
    entity: str
    attr: str
    model: type


@dataclass(frozen=True)
class EntityConfig:
    model: type
    search_fields: tuple[str, ...] = ()
    sort_field: str = "id"
    unique_fields: tuple[str, ...] = ()
    relation_fields: dict[str, str] = field(default_factory=dict)
    child_fields: dict[str, ChildConfig] = field(default_factory=dict)
    detail_loaders: tuple[Any, ...] = ()


ENTITY_CONFIGS: dict[str, EntityConfig] = {
    "paths": EntityConfig(
        model=LearningPath,
        search_fields=("slug", "target_goal", "level"),
        sort_field="order_index",
        unique_fields=("slug",),
        detail_loaders=(selectinload(LearningPath.courses),),
    ),
    "courses": EntityConfig(
        model=Course,
        search_fields=("slug",),
        sort_field="order_index",
        unique_fields=("slug",),
        detail_loaders=(selectinload(Course.modules), selectinload(Course.path)),
    ),
    "modules": EntityConfig(
        model=Module,
        search_fields=("slug", "difficulty"),
        sort_field="order_index",
        unique_fields=("slug",),
        detail_loaders=(selectinload(Module.lessons), selectinload(Module.course)),
    ),
    "lessons": EntityConfig(
        model=Lesson,
        search_fields=("slug", "topic", "difficulty"),
        sort_field="order_index",
        unique_fields=("slug",),
        relation_fields={
            "related_vocabulary": "related_vocabulary",
            "related_grammar": "related_grammar",
            "related_scenarios": "related_scenarios",
        },
        child_fields={
            "blocks": ChildConfig(entity="lesson-blocks", attr="blocks", model=LessonBlock),
            "assets": ChildConfig(entity="lesson-assets", attr="assets", model=LessonAsset),
        },
        detail_loaders=(
            selectinload(Lesson.module),
            selectinload(Lesson.blocks),
            selectinload(Lesson.assets),
            selectinload(Lesson.exercises).selectinload(Exercise.options),
            selectinload(Lesson.exercises).selectinload(Exercise.audio_assets),
            selectinload(Lesson.related_vocabulary),
            selectinload(Lesson.related_grammar),
            selectinload(Lesson.related_scenarios),
        ),
    ),
    "lesson-blocks": EntityConfig(model=LessonBlock, search_fields=("block_type",), sort_field="order_index"),
    "lesson-assets": EntityConfig(model=LessonAsset, search_fields=("asset_type", "url"), sort_field="id"),
    "exercises": EntityConfig(
        model=Exercise,
        search_fields=("slug", "exercise_type", "topic", "difficulty"),
        sort_field="order_index",
        unique_fields=("slug",),
        child_fields={"options": ChildConfig(entity="exercise-options", attr="options", model=ExerciseOption)},
        detail_loaders=(selectinload(Exercise.options), selectinload(Exercise.lesson), selectinload(Exercise.audio_assets)),
    ),
    "exercise-options": EntityConfig(model=ExerciseOption, search_fields=("value",), sort_field="order_index"),
    "vocabulary": EntityConfig(
        model=Vocabulary,
        search_fields=("slug", "korean", "topic", "difficulty"),
        sort_field="korean",
        unique_fields=("slug",),
        detail_loaders=(selectinload(Vocabulary.related_lessons), selectinload(Vocabulary.related_scenarios)),
    ),
    "grammar": EntityConfig(
        model=GrammarPoint,
        search_fields=("slug", "korean_pattern", "category", "difficulty"),
        sort_field="korean_pattern",
        unique_fields=("slug",),
        detail_loaders=(selectinload(GrammarPoint.related_lessons), selectinload(GrammarPoint.related_scenarios)),
    ),
    "example-sentences": EntityConfig(model=ExampleSentence, search_fields=("korean", "register"), sort_field="id"),
    "scenarios": EntityConfig(
        model=Scenario,
        search_fields=("slug", "topic", "difficulty"),
        sort_field="order_index",
        unique_fields=("slug",),
        relation_fields={
            "related_vocabulary": "related_vocabulary",
            "related_grammar": "related_grammar",
            "related_lessons": "related_lessons",
        },
        child_fields={"dialogues": ChildConfig(entity="dialogues", attr="dialogues", model=Dialogue)},
        detail_loaders=(
            selectinload(Scenario.dialogues).selectinload(Dialogue.dialogue_lines),
            selectinload(Scenario.related_vocabulary),
            selectinload(Scenario.related_grammar),
            selectinload(Scenario.related_lessons),
        ),
    ),
    "dialogues": EntityConfig(
        model=Dialogue,
        search_fields=("politeness_level",),
        sort_field="order_index",
        child_fields={"dialogue_lines": ChildConfig(entity="dialogue-lines", attr="dialogue_lines", model=DialogueLine)},
        detail_loaders=(selectinload(Dialogue.dialogue_lines), selectinload(Dialogue.scenario)),
    ),
    "dialogue-lines": EntityConfig(model=DialogueLine, search_fields=("speaker", "korean"), sort_field="order_index"),
    "audio-assets": EntityConfig(
        model=AudioAsset,
        search_fields=("public_id", "original_filename", "attachment_role", "variant", "compliance_state"),
        sort_field="updated_at",
        unique_fields=("public_id",),
        detail_loaders=(
            selectinload(AudioAsset.lesson),
            selectinload(AudioAsset.lesson_block),
            selectinload(AudioAsset.exercise),
            selectinload(AudioAsset.vocabulary),
            selectinload(AudioAsset.example_sentence),
            selectinload(AudioAsset.dialogue_line),
            selectinload(AudioAsset.scenario),
        ),
    ),
    "tags": EntityConfig(model=ContentTag, search_fields=("slug", "category"), sort_field="order_index", unique_fields=("slug",)),
    "localization": EntityConfig(model=LocalizationEntry, search_fields=("namespace", "key", "language"), sort_field="key", unique_fields=("namespace", "key", "language")),
    "premium-packs": EntityConfig(model=PremiumPack, search_fields=("slug", "currency"), sort_field="order_index", unique_fields=("slug",)),
}

SCAN_EXCLUDED_ENTITIES = {"lesson-assets"}


def dashboard(db: Session) -> DashboardSummary:
    payload = DashboardSummary()
    for entity, config in ENTITY_CONFIGS.items():
        if entity in SCAN_EXCLUDED_ENTITIES:
            continue
        model = config.model
        query = db.query(model)
        if hasattr(model, "is_deleted"):
            query = query.filter(model.is_deleted.is_(False))
        total = query.count()
        payload.entities[entity] = total
        entity_summary = DashboardEntitySummary(total=total)
        if hasattr(model, "status"):
            entity_summary.draft = query.filter(model.status == "draft").count()
            entity_summary.published = query.filter(model.status == "published").count()
            entity_summary.archived = query.filter(model.status == "archived").count()
            payload.drafts[entity] = entity_summary.draft
        if hasattr(model, "resolved_access_state"):
            entity_summary.premium = query.filter(model.resolved_access_state == "premium").count()
            payload.premium[entity] = entity_summary.premium
        payload.by_entity[entity] = entity_summary

    queue_items = _collect_publish_queue_items(db)
    validation_items = _collect_validation_center_items(db)
    payload.publish_queue_total = len(queue_items)
    payload.validation_issue_total = sum(item.error_count for item in validation_items)
    payload.validation_warning_total = sum(item.warning_count for item in validation_items)

    ready_by_entity: dict[str, int] = {}
    blocked_by_entity: dict[str, int] = {}
    warning_by_entity: dict[str, int] = {}
    for item in queue_items:
        if item.ready_to_publish:
            ready_by_entity[item.entity] = ready_by_entity.get(item.entity, 0) + 1
        else:
            blocked_by_entity[item.entity] = blocked_by_entity.get(item.entity, 0) + 1
        if item.warning_count:
            warning_by_entity[item.entity] = warning_by_entity.get(item.entity, 0) + 1

    for entity, summary in payload.by_entity.items():
        summary.ready_to_publish = ready_by_entity.get(entity, 0)
        summary.blocked = blocked_by_entity.get(entity, 0)
        summary.warnings = warning_by_entity.get(entity, 0)

    payload.overview = DashboardOverview(
        total_items=sum(item.total for item in payload.by_entity.values()),
        draft_items=sum(item.draft for item in payload.by_entity.values()),
        published_items=sum(item.published for item in payload.by_entity.values()),
        archived_items=sum(item.archived for item in payload.by_entity.values()),
        premium_items=sum(item.premium for item in payload.by_entity.values()),
        ready_to_publish=sum(item.ready_to_publish for item in payload.by_entity.values()),
        blocked_items=sum(item.blocked for item in payload.by_entity.values()),
        warning_items=sum(item.warnings for item in payload.by_entity.values()),
    )
    payload.audio_health = _audio_health_summary(db)
    return payload


def publish_queue(
    db: Session,
    *,
    entity: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PublishQueueResponse:
    items = _collect_publish_queue_items(db, entity=entity, q=q)
    return PublishQueueResponse(items=items[offset : offset + min(limit, 200)], total=len(items), limit=limit, offset=offset)


def validation_center(
    db: Session,
    *,
    entity: str | None = None,
    q: str | None = None,
    level: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ValidationCenterResponse:
    items = _collect_validation_center_items(db, entity=entity, q=q, level=level)
    return ValidationCenterResponse(items=items[offset : offset + min(limit, 200)], total=len(items), limit=limit, offset=offset)


def audit_trail(
    db: Session,
    *,
    entity: str | None = None,
    item_id: int | None = None,
    action: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> AuditTrailResponse:
    query = db.query(AdminAuditLog)
    if entity:
        query = query.filter(AdminAuditLog.entity_type == entity)
    if item_id is not None:
        query = query.filter(AdminAuditLog.entity_id == item_id)
    if action:
        query = query.filter(AdminAuditLog.action == action)

    total = query.count()
    rows = query.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc()).offset(offset).limit(min(limit, 200)).all()
    admin_ids = {row.admin_user_id for row in rows if row.admin_user_id is not None}
    admin_emails = {}
    if admin_ids:
        admin_emails = {admin.id: admin.email for admin in db.query(AdminUser).filter(AdminUser.id.in_(admin_ids)).all()}

    return AuditTrailResponse(
        items=[
            AuditTrailItem(
                id=row.id,
                created_at=row.created_at,
                admin_user_id=row.admin_user_id,
                admin_email=admin_emails.get(row.admin_user_id),
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                request_id=row.request_id,
                before=row.before,
                after=row.after,
            )
            for row in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


def record_admin_audit_event(
    db: Session,
    *,
    admin: AdminUser,
    action: str,
    entity: str,
    entity_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    _audit(db, admin, action, entity, entity_id, before, after, request_id)


def list_entities(
    db: Session,
    entity: str,
    *,
    q: str | None = None,
    status_filter: str | None = None,
    access_filter: str | None = None,
    topic: str | None = None,
    level: str | None = None,
    relation_id: int | None = None,
    relation_field: str | None = None,
    health_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str | None = None,
    sort_dir: str = "asc",
) -> dict[str, Any]:
    config = _config(entity)
    model = config.model
    query = db.query(model)
    if hasattr(model, "is_deleted"):
        query = query.filter(model.is_deleted.is_(False))
    if status_filter and hasattr(model, "status"):
        query = query.filter(model.status == status_filter)
    if access_filter and hasattr(model, "resolved_access_state"):
        query = query.filter(model.resolved_access_state == access_filter)
    if topic and hasattr(model, "topic"):
        query = query.filter(model.topic == topic)
    if level:
        if hasattr(model, "difficulty"):
            query = query.filter(model.difficulty == level)
        elif hasattr(model, "level"):
            query = query.filter(model.level == level)
    if relation_id and relation_field and hasattr(model, relation_field):
        query = query.filter(getattr(model, relation_field) == relation_id)
    if q:
        query = _apply_search(query, entity, q)
    sort_column = getattr(model, sort_by or config.sort_field, getattr(model, config.sort_field))
    if sort_dir == "desc":
        sort_column = sort_column.desc()
    if entity == "audio-assets" and health_filter:
        settings = get_settings()
        for loader in config.detail_loaders:
            query = query.options(loader)
        rows = [row for row in query.order_by(sort_column, model.id).all() if _audio_asset_matches_health_filter(row, health_filter, settings)]
        total = len(rows)
        rows = rows[offset : offset + min(limit, 200)]
        return {"items": [serialize_entity(entity, row) for row in rows], "total": total, "limit": limit, "offset": offset}
    total = query.count()
    rows = query.order_by(sort_column, model.id).offset(offset).limit(min(limit, 200)).all()
    return {"items": [serialize_entity(entity, row) for row in rows], "total": total, "limit": limit, "offset": offset}


def get_entity(db: Session, entity: str, item_id: int) -> dict[str, Any]:
    row = _get_with_loaders(db, entity, item_id)
    return serialize_entity(entity, row, detail=True)


def create_entity(db: Session, entity: str, payload: dict[str, Any], admin: AdminUser, request_id: str | None = None) -> dict[str, Any]:
    config = _config(entity)
    validation = validate_payload_entity(db, entity, payload)
    if payload.get("data", {}).get("status") == "published" and not validation.valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=validation.model_dump())
    row = config.model()
    data = _prepare_data(entity, payload.get("data") or {}, creating=True)
    _apply_row_data(row, data)
    _stamp_admin(row, admin, creating=True)
    db.add(row)
    db.flush()
    _sync_nested(db, entity, row, payload, admin)
    _after_save(entity, row)
    db.flush()
    _audit(db, admin, "create", entity, row.id, None, serialize_entity(entity, row, detail=True), request_id)
    db.commit()
    return get_entity(db, entity, row.id)


def update_entity(db: Session, entity: str, item_id: int, payload: dict[str, Any], admin: AdminUser, request_id: str | None = None) -> dict[str, Any]:
    row = _get_with_loaders(db, entity, item_id)
    validation = validate_payload_entity(db, entity, payload)
    next_status = payload.get("data", {}).get("status")
    if next_status == "published" and not validation.valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=validation.model_dump())
    before = serialize_entity(entity, row, detail=True)
    data = _prepare_data(entity, payload.get("data") or {}, creating=False)
    _apply_row_data(row, data)
    _stamp_admin(row, admin, creating=False)
    _sync_nested(db, entity, row, payload, admin)
    _after_save(entity, row)
    db.flush()
    _audit(db, admin, "update", entity, item_id, before, serialize_entity(entity, row, detail=True), request_id)
    db.commit()
    return get_entity(db, entity, item_id)


def delete_entity(db: Session, entity: str, item_id: int, admin: AdminUser, request_id: str | None = None) -> dict[str, bool]:
    row = _get_with_loaders(db, entity, item_id)
    before = serialize_entity(entity, row, detail=True)
    if hasattr(row, "is_deleted"):
        row.is_deleted = True
    if hasattr(row, "status"):
        row.status = "archived"
    _after_save(entity, row)
    _audit(db, admin, "delete", entity, item_id, before, None, request_id)
    db.commit()
    return {"ok": True}


def duplicate_entity(db: Session, entity: str, item_id: int, admin: AdminUser, request_id: str | None = None) -> dict[str, Any]:
    source = _get_with_loaders(db, entity, item_id)
    clone = _clone_row(db, entity, source, admin)
    db.add(clone)
    db.flush()
    _clone_children_and_relations(db, entity, source, clone, admin)
    _after_save(entity, clone)
    db.flush()
    _audit(db, admin, "duplicate", entity, clone.id, serialize_entity(entity, source, detail=True), serialize_entity(entity, clone, detail=True), request_id)
    db.commit()
    return get_entity(db, entity, clone.id)


def publish_entity(db: Session, entity: str, item_id: int, admin: AdminUser, request_id: str | None = None) -> dict[str, Any]:
    row = _get_with_loaders(db, entity, item_id)
    before = serialize_entity(entity, row, detail=True)
    validation = validate_current_entity(db, entity, item_id)
    if not validation.valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=validation.model_dump())
    if hasattr(row, "status"):
        row.status = "published"
    _publish_children(entity, row)
    _stamp_admin(row, admin, creating=False)
    _after_save(entity, row)
    _audit(db, admin, "publish", entity, item_id, before, serialize_entity(entity, row, detail=True), request_id)
    db.commit()
    return get_entity(db, entity, item_id)


def unpublish_entity(db: Session, entity: str, item_id: int, admin: AdminUser, request_id: str | None = None) -> dict[str, Any]:
    row = _get_with_loaders(db, entity, item_id)
    before = serialize_entity(entity, row, detail=True)
    if hasattr(row, "status"):
        row.status = "draft"
    _stamp_admin(row, admin, creating=False)
    _after_save(entity, row)
    _audit(db, admin, "unpublish", entity, item_id, before, serialize_entity(entity, row, detail=True), request_id)
    db.commit()
    return get_entity(db, entity, item_id)


def validate_payload_entity(db: Session, entity: str, payload: dict[str, Any]) -> ValidationResult:
    data = _prepare_data(entity, payload.get("data") or {}, creating=False)
    validation = ensure_publishable(db, entity, data, relation_ids=payload.get("relation_ids") or {}, children=payload.get("children") or {})
    _append_protected_audio_issues(validation, entity, data, payload.get("children") or {})
    return validation


def validate_current_entity(db: Session, entity: str, item_id: int) -> ValidationResult:
    row = _get_with_loaders(db, entity, item_id)
    detail = serialize_entity(entity, row, detail=True)
    return _validate_detail_entity(db, entity, detail, row=row)


def _validate_detail_entity(db: Session, entity: str, detail: dict[str, Any], *, row: Any | None = None) -> ValidationResult:
    data = {key: value for key, value in detail.items() if key not in {"relation_ids", "children", "display_label", "meta"}}
    validation = ensure_publishable(db, entity, data, relation_ids=detail.get("relation_ids") or {}, children=detail.get("children") or {})
    _append_protected_audio_issues(validation, entity, data, detail.get("children") or {})
    _append_required_audio_issues(validation, entity, row, detail)
    return validation


def reorder_entity(db: Session, entity: str, order: list[int], admin: AdminUser, request_id: str | None = None) -> dict[str, bool]:
    config = _config(entity)
    rows = db.query(config.model).filter(config.model.id.in_(order)).all()
    by_id = {row.id: row for row in rows}
    for index, item_id in enumerate(order):
        row = by_id.get(item_id)
        if row and hasattr(row, "order_index"):
            row.order_index = index
            _stamp_admin(row, admin, creating=False)
            _after_save(entity, row)
    _audit(db, admin, "reorder", entity, None, None, {"order": order}, request_id)
    db.commit()
    return {"ok": True}


def bulk_update_status(
    db: Session,
    *,
    entity: str,
    ids: list[int],
    status_value: str | None,
    access_state: str | None,
    admin: AdminUser,
    request_id: str | None = None,
) -> dict[str, int]:
    config = _config(entity)
    rows = db.query(config.model).filter(config.model.id.in_(ids)).all()
    updated = 0
    for row in rows:
        if status_value and hasattr(row, "status"):
            row.status = status_value
        if access_state and hasattr(row, "access_state"):
            row.access_state = access_state
        _stamp_admin(row, admin, creating=False)
        _after_save(entity, row)
        updated += 1
    _audit(db, admin, "bulk_update", entity, None, None, {"ids": ids, "status": status_value, "access_state": access_state}, request_id)
    db.commit()
    return {"updated": updated}


def build_preview(db: Session, entity: str, item_id: int, *, viewer_access: str = "free") -> PreviewResponse:
    row = _get_with_loaders(db, entity, item_id)
    detail = serialize_entity(entity, row, detail=True)
    return PreviewResponse(
        entity=entity,
        entity_id=item_id,
        viewer_access=viewer_access,
        learner_visible=_learner_visible_dict(detail),
        locked_for_viewer=detail.get("resolved_access_state") == "premium" and viewer_access != "premium",
        deep_link=_entity_deep_link(entity, row),
        data=_preview_payload(entity, detail),
    )


def export_entity(
    db: Session,
    entity: str,
    *,
    format_name: str = "json",
    admin: AdminUser | None = None,
    request_id: str | None = None,
) -> ExportResponse:
    rows = _export_rows(db, entity)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if format_name == "csv":
        content = _export_csv(entity, rows)
        mime_type = "text/csv"
        extension = "csv"
    else:
        content = json.dumps(
            {
                "schema_version": "phase_c.v1",
                "entity": entity,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "count": len(rows),
                "items": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        mime_type = "application/json"
        extension = "json"
    response = ExportResponse(
        entity=entity,
        format=format_name,
        filename=f"{entity}-{timestamp}.{extension}",
        mime_type=mime_type,
        content=content,
        count=len(rows),
    )
    if admin is not None:
        _audit(db, admin, "export", entity, None, None, {"format": format_name, "count": len(rows)}, request_id)
        db.commit()
    return response


def import_entity(db: Session, entity: str, request: ImportRequest, admin: AdminUser, request_id: str | None = None) -> ImportResult:
    items = _parse_import_content(entity, request)
    result = ImportResult(entity=entity, format=request.format, dry_run=request.dry_run)
    preview_items: list[dict[str, Any]] = []

    for index, raw_item in enumerate(items, start=1):
        payload = _normalize_import_item(entity, raw_item)
        validation = validate_payload_entity(db, entity, payload)
        if not validation.valid:
            for issue in validation.issues:
                if issue.level == "error":
                    result.errors.append({"row": index, "identifier": _import_identifier(entity, payload), "message": issue.message})
            continue

        preview_items.append(payload["data"])
        if request.dry_run:
            continue

        existing = _find_existing(db, entity, payload["data"])
        strategy = request.conflict_strategy
        if existing and strategy == "skip":
            result.skipped += 1
            continue
        if existing and strategy == "overwrite":
            update_entity(db, entity, existing.id, payload, admin, request_id)
            result.updated += 1
            continue
        if existing and strategy == "merge":
            merged = _merge_payload(serialize_entity(entity, existing, detail=True), payload)
            update_entity(db, entity, existing.id, merged, admin, request_id)
            result.merged += 1
            continue
        if existing and strategy == "create_new":
            payload["data"] = dict(payload["data"])
            if "slug" in payload["data"]:
                payload["data"]["slug"] = _copy_slug(db, _config(entity).model, payload["data"]["slug"])
            elif entity == "localization":
                payload["data"]["key"] = f"{payload['data']['key']}_copy"

        create_entity(db, entity, payload, admin, request_id)
        result.created += 1

    result.preview_items = preview_items[:10]
    _audit(
        db,
        admin,
        "import",
        entity,
        None,
        None,
        {"format": request.format, "dry_run": request.dry_run, "created": result.created, "updated": result.updated, "skipped": result.skipped},
        request_id,
    )
    if not request.dry_run:
        db.commit()
    return result


def template_export(entity: str, *, format_name: str = "json") -> ExportResponse:
    example_item = _example_payload(entity)
    if format_name == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(example_item.keys()))
        writer.writeheader()
        writer.writerow(example_item)
        return ExportResponse(entity=entity, format="csv", filename=f"{entity}-template.csv", mime_type="text/csv", content=output.getvalue(), count=1)
    content = json.dumps({"schema_version": "phase_c.v1", "entity": entity, "items": [example_item]}, ensure_ascii=False, indent=2)
    return ExportResponse(entity=entity, format="json", filename=f"{entity}-template.json", mime_type="application/json", content=content, count=1)


def relation_options(db: Session) -> dict[str, list[RelationOption]]:
    return {
        "paths": _summary_options(db, LearningPath),
        "courses": _summary_options(db, Course),
        "modules": _summary_options(db, Module),
        "lessons": _summary_options(db, Lesson),
        "lesson-blocks": _summary_options(db, LessonBlock),
        "exercises": _summary_options(db, Exercise),
        "vocabulary": _summary_options(db, Vocabulary),
        "grammar": _summary_options(db, GrammarPoint),
        "scenarios": _summary_options(db, Scenario),
        "dialogues": _summary_options(db, Dialogue),
        "dialogue-lines": _summary_options(db, DialogueLine),
        "example-sentences": _summary_options(db, ExampleSentence),
        "audio-assets": _summary_options(db, AudioAsset),
        "tags": _summary_options(db, ContentTag),
        "premium-packs": _summary_options(db, PremiumPack),
    }


def serialize_entity(entity: str, row: Any, *, detail: bool = False) -> dict[str, Any]:
    config = _config(entity)
    data = {column.key: getattr(row, column.key) for column in inspect(row.__class__).columns}
    data["display_label"] = _display_label(entity, row)
    data["meta"] = {"entity": entity}
    if entity == "audio-assets":
        settings = get_settings()
        data["health"] = audio_asset_admin_health(row, settings)
        preview_admin_id = row.updated_by_admin_id or row.created_by_admin_id
        if preview_admin_id:
            data["preview_url"] = admin_preview_url(row, preview_admin_id, settings)
        data["linked_entity"] = _audio_asset_parent(row)
    if detail:
        relation_ids: dict[str, list[int]] = {}
        for key, attr in config.relation_fields.items():
            relation_ids[key] = [item.id for item in getattr(row, attr)]
        children: dict[str, list[dict[str, Any]]] = {}
        for key, child_config in config.child_fields.items():
            child_rows = [item for item in getattr(row, child_config.attr) if not getattr(item, "is_deleted", False)]
            child_rows.sort(key=lambda item: (getattr(item, "order_index", 0), item.id))
            children[key] = [serialize_entity(child_config.entity, child, detail=True) for child in child_rows]
        if relation_ids:
            data["relation_ids"] = relation_ids
        if children:
            data["children"] = children
            if entity == "lessons":
                data["blocks"] = children.get("blocks", [])
                data["assets"] = children.get("assets", [])
            if entity == "exercises":
                data["options"] = children.get("options", [])
            if entity == "dialogues":
                data["dialogue_lines"] = children.get("dialogue_lines", [])
                data["lines"] = _dialogue_lines_payload(row)
            if entity == "scenarios":
                data["dialogues"] = children.get("dialogues", [])
        if entity == "lessons":
            data["exercise_ids"] = [exercise.id for exercise in row.exercises if not exercise.is_deleted]
            data["exercises"] = [
                serialize_entity("exercises", exercise, detail=True)
                for exercise in sorted((item for item in row.exercises if not item.is_deleted), key=lambda item: (item.order_index, item.id))
            ]
        if entity == "vocabulary":
            data["related_lesson_ids"] = [lesson.id for lesson in row.related_lessons]
            data["related_scenario_ids"] = [scenario.id for scenario in row.related_scenarios]
        if entity == "grammar":
            data["related_lesson_ids"] = [lesson.id for lesson in row.related_lessons]
            data["related_scenario_ids"] = [scenario.id for scenario in row.related_scenarios]
        if entity == "scenarios":
            data["target_vocabulary_ids"] = [item.id for item in row.related_vocabulary] or list(row.target_vocabulary_ids or [])
            data["target_grammar_ids"] = [item.id for item in row.related_grammar] or list(row.target_grammar_ids or [])
    return data


def _config(entity: str) -> EntityConfig:
    config = ENTITY_CONFIGS.get(entity)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown content entity: {entity}")
    return config


def _get_with_loaders(db: Session, entity: str, item_id: int) -> Any:
    config = _config(entity)
    query = db.query(config.model)
    for loader in config.detail_loaders:
        query = query.options(loader)
    row = query.filter(config.model.id == item_id).first()
    if not row or getattr(row, "is_deleted", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content item not found")
    return row


def _prepare_data(entity: str, data: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    payload = dict(data)
    if creating:
        payload.setdefault("status", "draft")
        if _config(entity).model in {Course, Module, Lesson, Exercise, Dialogue}:
            payload.setdefault("access_state", "inherit")
        elif hasattr(_config(entity).model, "access_state"):
            payload.setdefault("access_state", "free")
    if "resolved_access_state" in payload:
        payload.pop("resolved_access_state", None)
    if entity == "dialogues" and "dialogue_lines" in payload:
        payload.pop("dialogue_lines", None)
    if entity == "lessons" and "blocks" in payload:
        payload.pop("blocks", None)
    if entity == "lessons" and "assets" in payload:
        payload.pop("assets", None)
    if entity == "exercises" and "options" in payload:
        payload.pop("options", None)
    if entity == "scenarios" and "dialogues" in payload:
        payload.pop("dialogues", None)
    return payload


def _apply_row_data(row: Any, data: dict[str, Any]) -> None:
    columns = {column.key for column in inspect(row.__class__).columns}
    for key, value in data.items():
        if key in columns and key not in {"id", "created_at", "updated_at"}:
            setattr(row, key, value)


def _stamp_admin(row: Any, admin: AdminUser, *, creating: bool) -> None:
    if hasattr(row, "updated_by_admin_id"):
        row.updated_by_admin_id = admin.id
    if creating and hasattr(row, "created_by_admin_id") and getattr(row, "created_by_admin_id", None) is None:
        row.created_by_admin_id = admin.id


def _sync_nested(db: Session, entity: str, row: Any, payload: dict[str, Any], admin: AdminUser) -> None:
    detail_children = payload.get("children") or {}
    relation_ids = payload.get("relation_ids") or {}
    config = _config(entity)
    for key, attr in config.relation_fields.items():
        if key in relation_ids:
            model = _relation_model(key)
            rows = db.query(model).filter(model.id.in_(relation_ids[key])).all() if relation_ids[key] else []
            setattr(row, attr, rows)
    for key, child_config in config.child_fields.items():
        if key in detail_children:
            _sync_child_collection(db, row, child_config, detail_children[key], admin)


def _sync_child_collection(db: Session, parent: Any, child_config: ChildConfig, payloads: list[dict[str, Any]], admin: AdminUser) -> None:
    existing_rows = list(getattr(parent, child_config.attr))
    existing_by_id = {row.id: row for row in existing_rows if row.id is not None}
    seen_ids: set[int] = set()
    target_collection = getattr(parent, child_config.attr)

    for index, item in enumerate(payloads):
        item = dict(item)
        item.setdefault("order_index", index)
        child = existing_by_id.get(item.get("id"))
        if child is None:
            child = child_config.model()
            target_collection.append(child)
        else:
            seen_ids.add(child.id)
        nested_payload = item.pop("children", {})
        if child_config.entity == "dialogues" and "dialogue_lines" in item:
            nested_payload = {**nested_payload, "dialogue_lines": item.pop("dialogue_lines")}
        if child_config.entity == "exercises" and "options" in item:
            nested_payload = {**nested_payload, "options": item.pop("options")}
        _apply_row_data(child, item)
        _stamp_admin(child, admin, creating=child.id is None)
        _sync_nested(db, child_config.entity, child, {"data": item, "children": nested_payload}, admin)
        _after_save(child_config.entity, child)

    for row in existing_rows:
        if row.id and row.id not in seen_ids:
            if hasattr(row, "is_deleted"):
                row.is_deleted = True
            else:
                target_collection.remove(row)


def _after_save(entity: str, row: Any) -> None:
    sync_access_state(row)
    if entity == "audio-assets":
        row.published_at = utcnow() if getattr(row, "status", "draft") == "published" else None
    if entity == "dialogues":
        row.lines = _dialogue_lines_payload(row)
        row.useful_expressions = [
            {"korean": line.korean, "translations": line.translations}
            for line in sorted((item for item in row.dialogue_lines if not getattr(item, "is_deleted", False)), key=lambda item: item.order_index)
            if line.is_useful_expression
        ]
    if entity == "scenarios":
        row.target_vocabulary_ids = [item.id for item in row.related_vocabulary]
        row.target_grammar_ids = [item.id for item in row.related_grammar]
    if entity in {"paths", "courses", "modules", "lessons", "scenarios"}:
        propagate_access_state(row)


def _publish_children(entity: str, row: Any) -> None:
    if entity == "lessons":
        for block in row.blocks:
            if not block.is_deleted:
                block.status = "published"
    if entity == "scenarios":
        for dialogue in row.dialogues:
            if not dialogue.is_deleted:
                dialogue.status = "published"
    if entity == "dialogues":
        for line in row.dialogue_lines:
            if hasattr(line, "is_deleted") and getattr(line, "is_deleted"):
                continue


def _clone_row(db: Session, entity: str, source: Any, admin: AdminUser) -> Any:
    config = _config(entity)
    columns = {column.key: getattr(source, column.key) for column in inspect(source.__class__).columns}
    columns.pop("id", None)
    columns.pop("created_at", None)
    columns.pop("updated_at", None)
    if "slug" in columns:
        columns["slug"] = _copy_slug(db, config.model, columns["slug"])
    if "status" in columns:
        columns["status"] = "draft"
    clone = config.model()
    _apply_row_data(clone, columns)
    _stamp_admin(clone, admin, creating=True)
    return clone


def _clone_children_and_relations(db: Session, entity: str, source: Any, clone: Any, admin: AdminUser) -> None:
    config = _config(entity)
    for key, attr in config.relation_fields.items():
        setattr(clone, attr, list(getattr(source, attr)))
    for key, child_config in config.child_fields.items():
        for child in getattr(source, child_config.attr):
            if getattr(child, "is_deleted", False):
                continue
            cloned_child = _clone_row(db, child_config.entity, child, admin)
            getattr(clone, child_config.attr).append(cloned_child)
            db.flush()
            _clone_children_and_relations(db, child_config.entity, child, cloned_child, admin)
            _after_save(child_config.entity, cloned_child)
    if entity == "lessons":
        for exercise in source.exercises:
            if exercise.is_deleted:
                continue
            cloned_exercise = _clone_row(db, "exercises", exercise, admin)
            clone.exercises.append(cloned_exercise)
            db.flush()
            _clone_children_and_relations(db, "exercises", exercise, cloned_exercise, admin)
            _after_save("exercises", cloned_exercise)


def _copy_slug(db: Session, model: type, base_slug: str) -> str:
    candidate = f"{base_slug}-copy"
    index = 2
    while db.query(model).filter(model.slug == candidate).first():
        candidate = f"{base_slug}-copy-{index}"
        index += 1
    return candidate


def _append_protected_audio_issues(validation: ValidationResult, entity: str, data: dict[str, Any], children: dict[str, Any]) -> None:
    issues = _protected_audio_issues(entity, data, children)
    if not issues:
        return
    validation.valid = False
    existing = {(issue.code, issue.field, issue.message) for issue in validation.issues}
    for issue in issues:
        signature = (issue.code, issue.field, issue.message)
        if signature not in existing:
            validation.issues.append(issue)
            existing.add(signature)


def _protected_audio_issues(entity: str, data: dict[str, Any], children: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    message = "Premium listening audio must be attached through Audio Assets, not raw audio URLs."

    if entity == "vocabulary" and data.get("audio_asset_url"):
        issues.append(_audio_validation_issue("audio_asset_url", message))
    if entity == "dialogue-lines" and data.get("audio_asset_url"):
        issues.append(_audio_validation_issue("audio_asset_url", message))
    if entity in {"lesson-blocks", "exercises"} and _payload_has_legacy_audio(data.get("payload")):
        issues.append(_audio_validation_issue("payload.audio_asset_url", message))
    if entity == "lesson-assets" and _legacy_audio_lesson_asset(data):
        issues.append(
            _audio_validation_issue(
                "url",
                "Lesson-level premium listening tracks now belong in Audio Assets. Keep lesson assets for non-audio support files only.",
            )
        )
    if entity == "lessons":
        for index, block in enumerate(children.get("blocks") or []):
            issues.extend(_prefix_audio_issues(_protected_audio_issues("lesson-blocks", block, block.get("children") or {}), f"children.blocks[{index}]"))
        for index, asset in enumerate(children.get("assets") or []):
            issues.extend(_prefix_audio_issues(_protected_audio_issues("lesson-assets", asset, asset.get("children") or {}), f"children.assets[{index}]"))
    if entity == "dialogues":
        lines = children.get("dialogue_lines") or data.get("dialogue_lines") or []
        for index, line in enumerate(lines):
            issues.extend(_prefix_audio_issues(_protected_audio_issues("dialogue-lines", line, line.get("children") or {}), f"children.dialogue_lines[{index}]"))
    if entity == "scenarios":
        dialogues = children.get("dialogues") or data.get("dialogues") or []
        for index, dialogue in enumerate(dialogues):
            nested_children = dict(dialogue.get("children") or {})
            if "dialogue_lines" not in nested_children and dialogue.get("dialogue_lines"):
                nested_children["dialogue_lines"] = dialogue.get("dialogue_lines")
            issues.extend(_prefix_audio_issues(_protected_audio_issues("dialogues", dialogue, nested_children), f"children.dialogues[{index}]"))
    return issues


def _audio_validation_issue(field: str, message: str) -> ValidationIssue:
    return ValidationIssue(level="error", code="premium_audio_protected", field=field, message=message)


def _prefix_audio_issues(issues: list[ValidationIssue], prefix: str) -> list[ValidationIssue]:
    return [
        ValidationIssue(level=issue.level, code=issue.code, field=f"{prefix}.{issue.field}" if issue.field else prefix, message=issue.message)
        for issue in issues
    ]


def _payload_has_legacy_audio(payload: Any) -> bool:
    return isinstance(payload, dict) and any(payload.get(key) for key in ("audio_asset_url", "audio_url"))


def _legacy_audio_lesson_asset(data: dict[str, Any]) -> bool:
    asset_type = str(data.get("asset_type") or "")
    url = str(data.get("url") or "")
    if "audio" in asset_type.lower():
        return True
    if not url:
        return False
    clean_url = url.split("?", 1)[0].split("#", 1)[0]
    return Path(clean_url).suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def _collect_publish_queue_items(db: Session, *, entity: str | None = None, q: str | None = None) -> list[PublishQueueItem]:
    items: list[PublishQueueItem] = []
    for entity_name in _scannable_entities(entity):
        config = _config(entity_name)
        model = config.model
        if not hasattr(model, "status"):
            continue
        query = db.query(model)
        for loader in config.detail_loaders:
            query = query.options(loader)
        if hasattr(model, "is_deleted"):
            query = query.filter(model.is_deleted.is_(False))
        rows = query.filter(model.status == "draft").order_by(getattr(model, "updated_at", model.id).desc(), model.id.desc()).all()
        for row in rows:
            detail = serialize_entity(entity_name, row, detail=True)
            validation = _validate_detail_entity(db, entity_name, detail, row=row)
            label = detail.get("display_label") or _display_label(entity_name, row)
            if q and q.lower() not in str(label).lower():
                continue
            error_count = sum(1 for issue in validation.issues if issue.level == "error")
            warning_count = sum(1 for issue in validation.issues if issue.level == "warning")
            items.append(
                PublishQueueItem(
                    entity=entity_name,
                    entity_id=row.id,
                    label=str(label),
                    status=getattr(row, "status", None),
                    updated_at=getattr(row, "updated_at", None),
                    ready_to_publish=error_count == 0,
                    error_count=error_count,
                    warning_count=warning_count,
                    deep_link=_entity_deep_link(entity_name, row),
                    issues=validation.issues,
                )
            )
    items.sort(key=lambda item: ((0 if not item.ready_to_publish else 1), -(item.updated_at.timestamp() if item.updated_at else 0), item.entity, item.entity_id))
    return items


def _collect_validation_center_items(
    db: Session,
    *,
    entity: str | None = None,
    q: str | None = None,
    level: str | None = None,
) -> list[ValidationCenterItem]:
    items: list[ValidationCenterItem] = []
    for entity_name in _scannable_entities(entity):
        config = _config(entity_name)
        query = db.query(config.model)
        for loader in config.detail_loaders:
            query = query.options(loader)
        if hasattr(config.model, "is_deleted"):
            query = query.filter(config.model.is_deleted.is_(False))
        rows = query.order_by(getattr(config.model, "updated_at", config.model.id).desc(), config.model.id.desc()).all()
        for row in rows:
            detail = serialize_entity(entity_name, row, detail=True)
            validation = _validate_detail_entity(db, entity_name, detail, row=row)
            filtered_issues = validation.issues if not level else [issue for issue in validation.issues if issue.level == level]
            if not filtered_issues:
                continue
            label = detail.get("display_label") or _display_label(entity_name, row)
            if q and q.lower() not in str(label).lower():
                continue
            items.append(
                ValidationCenterItem(
                    entity=entity_name,
                    entity_id=row.id,
                    label=str(label),
                    status=getattr(row, "status", None),
                    updated_at=getattr(row, "updated_at", None),
                    error_count=sum(1 for issue in filtered_issues if issue.level == "error"),
                    warning_count=sum(1 for issue in filtered_issues if issue.level == "warning"),
                    deep_link=_entity_deep_link(entity_name, row),
                    issues=filtered_issues,
                )
            )
    items.sort(key=lambda item: (-item.error_count, -item.warning_count, -(item.updated_at.timestamp() if item.updated_at else 0), item.entity, item.entity_id))
    return items


def _scannable_entities(entity: str | None = None) -> list[str]:
    if entity:
        return [] if entity in SCAN_EXCLUDED_ENTITIES else [entity]
    return [name for name, config in ENTITY_CONFIGS.items() if name not in SCAN_EXCLUDED_ENTITIES and hasattr(config.model, "status")]


def _audio_health_summary(db: Session) -> dict[str, int]:
    settings = get_settings()
    rows = db.query(AudioAsset).filter(AudioAsset.is_deleted.is_(False)).all()
    summary = {"healthy": 0, "broken": 0, "missing": 0, "disabled": 0, "unpublished": 0, "expiring_soon": 0}
    for row in rows:
        health = audio_asset_admin_health(row, settings)
        state = str(health.get("state") or "healthy")
        if state not in summary:
            summary[state] = 0
        summary[state] += 1
        if health.get("expiring_soon"):
            summary["expiring_soon"] += 1
    return summary


def _append_required_audio_issues(validation: ValidationResult, entity: str, row: Any | None, detail: dict[str, Any]) -> None:
    issues: list[ValidationIssue] = []
    if entity == "exercises" and _exercise_requires_audio(detail):
        audio_assets = getattr(row, "audio_assets", []) if row is not None else []
        has_audio = any(not getattr(asset, "is_deleted", False) and asset.status == "published" and asset.compliance_state == "active" for asset in audio_assets)
        if not has_audio:
            issues.append(
                ValidationIssue(
                    level="error",
                    code="missing_audio_reference",
                    field="audio_assets",
                    message="Listening exercises require an active published Audio Asset before publish.",
                )
            )
    if entity == "lessons":
        exercises = detail.get("exercises") or []
        for index, exercise in enumerate(exercises, start=1):
            if not _exercise_requires_audio(exercise):
                continue
            if not _exercise_has_audio_reference(row, exercise.get("id")):
                issues.append(
                    ValidationIssue(
                        level="error",
                        code="missing_audio_reference",
                        field=f"exercises[{index}]",
                        message=f"Listening exercise {exercise.get('slug') or exercise.get('id') or index} is missing a published Audio Asset.",
                    )
                )
    if not issues:
        return
    validation.valid = False
    existing = {(issue.code, issue.field, issue.message) for issue in validation.issues}
    for issue in issues:
        signature = (issue.code, issue.field, issue.message)
        if signature not in existing:
            validation.issues.append(issue)
            existing.add(signature)


def _exercise_requires_audio(detail: dict[str, Any]) -> bool:
    return str(detail.get("exercise_type") or "") in {"listen_and_choose", "listen_and_order", "listen_and_match"}


def _exercise_has_audio_reference(row: Any | None, exercise_id: int | None) -> bool:
    if row is None or exercise_id is None:
        return False
    exercises = getattr(row, "exercises", []) or []
    for exercise in exercises:
        if exercise.id != exercise_id:
            continue
        for asset in getattr(exercise, "audio_assets", []) or []:
            if not getattr(asset, "is_deleted", False) and asset.status == "published" and asset.compliance_state == "active":
                return True
    return False


def _entity_deep_link(entity: str, row: Any) -> str | None:
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()
    if not bot_username:
        return None
    if entity == "lessons":
        return f"https://t.me/{bot_username}?start=lesson_{row.id}"
    if entity == "scenarios":
        return f"https://t.me/{bot_username}?start=scenario_{row.slug}"
    if entity == "dialogues":
        return f"https://t.me/{bot_username}?start=dialogue_{row.id}"
    return None


def _apply_search(query, entity: str, q: str):
    config = _config(entity)
    model = config.model
    clauses = []
    for field in config.search_fields:
        if hasattr(model, field):
            clauses.append(getattr(model, field).ilike(f"%{q}%"))
    if clauses:
        return query.filter(or_(*clauses))
    return query


def _relation_model(key: str) -> type:
    mapping = {
        "related_vocabulary": Vocabulary,
        "related_grammar": GrammarPoint,
        "related_scenarios": Scenario,
        "related_lessons": Lesson,
    }
    return mapping[key]


def _audit(
    db: Session,
    admin: AdminUser,
    action: str,
    entity: str,
    entity_id: int | None,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    request_id: str | None,
) -> None:
    db.add(
        AdminAuditLog(
            admin_user_id=admin.id,
            action=action,
            entity_type=entity,
            entity_id=entity_id,
            before=before,
            after=after,
            request_id=request_id,
        )
    )


def _display_label(entity: str, row: Any) -> str:
    if hasattr(row, "title") and isinstance(row.title, dict):
        return row.title.get("en") or next((value for value in row.title.values() if value), None) or getattr(row, "slug", str(row.id))
    for field in ("original_filename", "public_id", "korean", "korean_pattern", "namespace", "key", "slug", "value"):
        value = getattr(row, field, None)
        if value:
            return str(value)
    if entity == "dialogues":
        return f"Dialogue #{row.id}"
    if entity == "audio-assets":
        return f"Audio {row.public_id}"
    return str(row.id)


def _audio_asset_parent(row: AudioAsset) -> dict[str, Any] | None:
    mapping = [
        ("lesson", row.lesson),
        ("lesson-block", row.lesson_block),
        ("exercise", row.exercise),
        ("vocabulary", row.vocabulary),
        ("example-sentence", row.example_sentence),
        ("dialogue-line", row.dialogue_line),
        ("scenario", row.scenario),
    ]
    for entity, parent in mapping:
        if parent is not None:
            return {"entity": entity, "id": parent.id, "label": _display_label(entity, parent)}
    return None


def _dialogue_lines_payload(dialogue: Dialogue) -> list[dict[str, Any]]:
    lines = []
    for line in sorted((item for item in dialogue.dialogue_lines if not getattr(item, "is_deleted", False)), key=lambda item: item.order_index):
        lines.append(
            {
                "id": line.id,
                "speaker": line.speaker,
                "korean": line.korean,
                "translations": line.translations,
                "notes": line.notes,
                "audio_asset_url": line.audio_asset_url,
                "reveal_mode": line.reveal_mode,
                "highlighted_expressions": line.highlighted_expressions,
                "is_useful_expression": line.is_useful_expression,
                "order_index": line.order_index,
            }
        )
    return lines


def _learner_visible_dict(data: dict[str, Any]) -> bool:
    return data.get("status") == "published" and not data.get("is_deleted") and data.get("resolved_access_state") not in {"hidden", "internal"}


def _preview_payload(entity: str, detail: dict[str, Any]) -> dict[str, Any]:
    if entity == "lessons":
        return {
            "title": detail.get("title"),
            "summary": detail.get("summary"),
            "objectives": detail.get("objectives", []),
            "has_audio": detail.get("has_audio", False),
            "assets": detail.get("assets", []),
            "blocks": detail.get("blocks", []),
            "exercises": detail.get("exercises", []),
            "relation_ids": detail.get("relation_ids", {}),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "scenarios":
        return {
            "title": detail.get("title"),
            "description": detail.get("description"),
            "roles": detail.get("roles", []),
            "dialogues": detail.get("dialogues", []),
            "relation_ids": detail.get("relation_ids", {}),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "dialogues":
        return {
            "title": detail.get("title"),
            "lines": detail.get("lines", []),
            "checks": detail.get("checks", []),
            "useful_expressions": detail.get("useful_expressions", []),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "vocabulary":
        return {
            "korean": detail.get("korean"),
            "translations": detail.get("translations"),
            "audio_asset_url": detail.get("audio_asset_url"),
            "example_sentences": detail.get("example_sentences", []),
            "notes": detail.get("notes", {}),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "grammar":
        return {
            "korean_pattern": detail.get("korean_pattern"),
            "title": detail.get("title"),
            "explanation": detail.get("explanation"),
            "usage_notes": detail.get("usage_notes", {}),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "exercises":
        return {
            "prompt": detail.get("prompt"),
            "instructions": detail.get("instructions", {}),
            "exercise_type": detail.get("exercise_type"),
            "options": detail.get("options", []),
            "answer_key": detail.get("answer_key", {}),
            "access_state": detail.get("resolved_access_state"),
        }
    if entity == "audio-assets":
        return {
            "public_id": detail.get("public_id"),
            "label": detail.get("label"),
            "attachment_role": detail.get("attachment_role"),
            "variant": detail.get("variant"),
            "storage_backend": detail.get("storage_backend"),
            "original_filename": detail.get("original_filename"),
            "mime_type": detail.get("mime_type"),
            "size_bytes": detail.get("size_bytes"),
            "duration_seconds": detail.get("duration_seconds"),
            "transcript_mode": detail.get("transcript_mode"),
            "premium_only": detail.get("premium_only"),
            "status": detail.get("status"),
            "compliance_state": detail.get("compliance_state"),
            "expires_at": detail.get("expires_at"),
            "health": detail.get("health"),
            "preview_url": detail.get("preview_url"),
            "linked_entity": detail.get("linked_entity"),
        }
    return detail


def _export_rows(db: Session, entity: str) -> list[dict[str, Any]]:
    config = _config(entity)
    query = db.query(config.model)
    for loader in config.detail_loaders:
        query = query.options(loader)
    if hasattr(config.model, "is_deleted"):
        query = query.filter(config.model.is_deleted.is_(False))
    rows = query.order_by(getattr(config.model, config.sort_field, config.model.id), config.model.id).all()
    return [serialize_entity(entity, row, detail=True) for row in rows]


def _export_csv(entity: str, rows: list[dict[str, Any]]) -> str:
    if entity not in {"vocabulary", "grammar"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV export is supported for vocabulary and grammar only.")
    flattened = [_flatten_csv_row(entity, row) for row in rows]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(flattened[0].keys()) if flattened else list(_flatten_csv_row(entity, _example_payload(entity)).keys()))
    writer.writeheader()
    for row in flattened:
        writer.writerow(row)
    return output.getvalue()


def _parse_import_content(entity: str, request: ImportRequest) -> list[dict[str, Any]]:
    if request.format == "csv":
        reader = csv.DictReader(io.StringIO(request.content))
        return [_expand_csv_row(entity, row) for row in reader]
    parsed = json.loads(request.content)
    if isinstance(parsed, dict) and "items" in parsed:
        return parsed["items"]
    if isinstance(parsed, list):
        return parsed
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid import payload.")


def _normalize_import_item(entity: str, item: dict[str, Any]) -> dict[str, Any]:
    relation_ids = item.get("relation_ids") or {}
    children = item.get("children") or {}
    if entity == "lessons" and "blocks" in item:
        children = {**children, "blocks": item["blocks"]}
    if entity == "scenarios" and "dialogues" in item:
        children = {**children, "dialogues": item["dialogues"]}
    if entity == "dialogues" and "dialogue_lines" in item:
        children = {**children, "dialogue_lines": item["dialogue_lines"]}
    if entity == "exercises" and "options" in item:
        children = {**children, "options": item["options"]}
    data = {key: value for key, value in item.items() if key not in {"id", "display_label", "meta", "relation_ids", "children", "blocks", "dialogues", "dialogue_lines", "options"}}
    return {"data": data, "relation_ids": relation_ids, "children": children}


def _find_existing(db: Session, entity: str, data: dict[str, Any]) -> Any | None:
    config = _config(entity)
    query = db.query(config.model)
    if entity == "localization":
        return (
            query.filter(
                LocalizationEntry.namespace == data.get("namespace"),
                LocalizationEntry.key == data.get("key"),
                LocalizationEntry.language == data.get("language"),
            ).first()
        )
    for field in config.unique_fields:
        value = data.get(field)
        if value:
            return query.filter(getattr(config.model, field) == value).first()
    return None


def _merge_payload(existing_detail: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = {
        "data": {**existing_detail, **incoming.get("data", {})},
        "relation_ids": {**(existing_detail.get("relation_ids") or {}), **(incoming.get("relation_ids") or {})},
        "children": {**(existing_detail.get("children") or {}), **(incoming.get("children") or {})},
    }
    for key in ("display_label", "meta", "id", "created_at", "updated_at", "resolved_access_state"):
        merged["data"].pop(key, None)
    return merged


def _import_identifier(entity: str, payload: dict[str, Any]) -> str | None:
    if "slug" in payload.get("data", {}):
        return str(payload["data"]["slug"])
    if entity == "localization":
        return f"{payload['data'].get('namespace')}:{payload['data'].get('key')}:{payload['data'].get('language')}"
    return None


def _flatten_csv_row(entity: str, row: dict[str, Any]) -> dict[str, Any]:
    if entity == "vocabulary":
        return {
            "slug": row.get("slug", ""),
            "korean": row.get("korean", ""),
            "reading": row.get("reading", ""),
            "topic": row.get("topic", ""),
            "difficulty": row.get("difficulty", ""),
            "access_state": row.get("access_state", "free"),
            "status": row.get("status", "draft"),
            "ru": (row.get("translations") or {}).get("ru", ""),
            "uz": (row.get("translations") or {}).get("uz", ""),
            "en": (row.get("translations") or {}).get("en", ""),
        }
    return {
        "slug": row.get("slug", ""),
        "korean_pattern": row.get("korean_pattern", ""),
        "category": row.get("category", ""),
        "difficulty": row.get("difficulty", ""),
        "access_state": row.get("access_state", "free"),
        "status": row.get("status", "draft"),
        "title_ru": (row.get("title") or {}).get("ru", ""),
        "title_uz": (row.get("title") or {}).get("uz", ""),
        "title_en": (row.get("title") or {}).get("en", ""),
        "explanation_ru": (row.get("explanation") or {}).get("ru", ""),
        "explanation_uz": (row.get("explanation") or {}).get("uz", ""),
        "explanation_en": (row.get("explanation") or {}).get("en", ""),
    }


def _expand_csv_row(entity: str, row: dict[str, str]) -> dict[str, Any]:
    if entity == "vocabulary":
        return {
            "slug": row.get("slug", ""),
            "korean": row.get("korean", ""),
            "reading": row.get("reading", ""),
            "topic": row.get("topic", "general"),
            "difficulty": row.get("difficulty", "A0"),
            "access_state": row.get("access_state", "free"),
            "status": row.get("status", "draft"),
            "translations": {"ru": row.get("ru", ""), "uz": row.get("uz", ""), "en": row.get("en", "")},
            "usage_notes": {"ru": "", "uz": "", "en": ""},
        }
    return {
        "slug": row.get("slug", ""),
        "korean_pattern": row.get("korean_pattern", ""),
        "category": row.get("category", "grammar"),
        "difficulty": row.get("difficulty", "A0"),
        "access_state": row.get("access_state", "free"),
        "status": row.get("status", "draft"),
        "title": {"ru": row.get("title_ru", ""), "uz": row.get("title_uz", ""), "en": row.get("title_en", "")},
        "explanation": {
            "ru": row.get("explanation_ru", ""),
            "uz": row.get("explanation_uz", ""),
            "en": row.get("explanation_en", ""),
        },
    }


def _summary_options(db: Session, model: type) -> list[RelationOption]:
    query = db.query(model)
    if hasattr(model, "is_deleted"):
        query = query.filter(model.is_deleted.is_(False))
    rows = query.order_by(getattr(model, "order_index", model.id), model.id).limit(250).all()
    return [RelationOption(id=row.id, label=_display_label(model.__tablename__, row), slug=getattr(row, "slug", None), meta=_option_meta(row)) for row in rows]


def _audio_asset_matches_health_filter(asset: AudioAsset, health_filter: str, settings) -> bool:
    health = audio_asset_admin_health(asset, settings)
    if health_filter == "expiring_soon":
        return bool(health["expiring_soon"])
    if health_filter == "unpublished":
        return health["state"] == "unpublished"
    if health_filter == "broken":
        return health["state"] == "broken"
    if health_filter == "missing":
        return health["state"] == "missing"
    if health_filter == "disabled":
        return health["state"] == "disabled"
    return True


def _option_meta(row: Any) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    for field in ("status", "resolved_access_state", "difficulty", "topic", "category"):
        if hasattr(row, field):
            meta[field] = getattr(row, field)
    return meta


def _example_payload(entity: str) -> dict[str, Any]:
    if entity == "lessons":
        return {
            "slug": "survival-greetings-01",
            "module_id": 1,
            "title": {"ru": "Приветствия", "uz": "Salomlashuv", "en": "Greetings"},
            "summary": {"ru": "Базовые приветствия", "uz": "Asosiy salomlashuv", "en": "Basic greetings"},
            "objectives": ["Recognize hello/thank you", "Practice polite greeting"],
            "difficulty": "A0",
            "topic": "survival",
            "access_state": "free",
            "status": "draft",
            "relation_ids": {"related_vocabulary": [1], "related_grammar": [1], "related_scenarios": [1]},
            "blocks": [
                {
                    "block_type": "explanation",
                    "title": {"ru": "Фокус", "uz": "Fokus", "en": "Focus"},
                    "body": {"ru": "안녕하세요 используется в вежливой речи.", "uz": "안녕하세요 muloyim nutqda ishlatiladi.", "en": "안녕하세요 is used in polite speech."},
                    "payload": {},
                    "order_index": 0,
                    "status": "draft",
                }
            ],
        }
    if entity == "vocabulary":
        return {
            "slug": "annyeonghaseyo",
            "korean": "안녕하세요",
            "reading": "annyeonghaseyo",
            "translations": {"ru": "Здравствуйте", "uz": "Salom", "en": "Hello"},
            "usage_notes": {"ru": "Вежливое приветствие", "uz": "Muloyim salomlashuv", "en": "Polite greeting"},
            "topic": "survival",
            "difficulty": "A0",
            "status": "draft",
            "access_state": "free",
        }
    if entity == "grammar":
        return {
            "slug": "topic-particle-neun-eun",
            "korean_pattern": "은/는",
            "title": {"ru": "Тематическая частица", "uz": "Mavzu qo'shimchasi", "en": "Topic particle"},
            "explanation": {
                "ru": "Используется для обозначения темы.",
                "uz": "Mavzuni ko'rsatish uchun ishlatiladi.",
                "en": "Used to mark the topic of a sentence.",
            },
            "category": "particles",
            "difficulty": "A0",
            "status": "draft",
            "access_state": "free",
        }
    if entity == "scenarios":
        return {
            "slug": "cafe-ordering-basic",
            "title": {"ru": "Кафе", "uz": "Kafe", "en": "At the cafe"},
            "description": {"ru": "Заказ кофе", "uz": "Qahva buyurtma qilish", "en": "Ordering coffee"},
            "roles": ["Customer", "Barista"],
            "topic": "food",
            "difficulty": "A0",
            "status": "draft",
            "access_state": "free",
            "relation_ids": {"related_vocabulary": [1], "related_grammar": [1], "related_lessons": [1]},
            "dialogues": [
                {
                    "title": {"ru": "Заказ", "uz": "Buyurtma", "en": "Order"},
                    "context": {"ru": "У стойки", "uz": "Peshtaxta oldida", "en": "At the counter"},
                    "status": "draft",
                    "access_state": "inherit",
                    "dialogue_lines": [
                        {
                            "speaker": "Customer",
                            "korean": "아메리카노 한 잔 주세요.",
                            "translations": {"ru": "Один американо, пожалуйста.", "uz": "Bitta americano, iltimos.", "en": "One Americano, please."},
                            "order_index": 0,
                        }
                    ],
                }
            ],
        }
    if entity == "localization":
        return {"namespace": "admin.lesson", "key": "publish", "language": "en", "value": "Publish", "status": "draft"}
    return {"slug": f"{entity}-sample", "status": "draft"}
