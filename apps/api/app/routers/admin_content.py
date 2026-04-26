from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.admin_schemas import (
    AdminBulkStatusRequest,
    AdminContentListResponse,
    AdminContentWriteRequest,
    AdminReorderRequest,
    ContentOptionsResponse,
    ExportResponse,
    ImportRequest,
    ImportResult,
    PreviewResponse,
    ValidationResult,
)
from app.core.db import get_db
from app.core.security import get_current_admin
from app.core.config import Settings, get_settings
from app.models.schema import AdminUser, AudioAsset
from app.services.admin_content_service import (
    build_preview,
    bulk_update_status,
    create_entity,
    dashboard,
    delete_entity,
    duplicate_entity,
    export_entity,
    get_entity,
    import_entity,
    list_entities,
    publish_entity,
    relation_options,
    reorder_entity,
    template_export,
    unpublish_entity,
    update_entity,
    validate_current_entity,
    validate_payload_entity,
)
from app.services.audio_service import create_audio_asset_from_upload, replace_audio_asset_file

router = APIRouter(prefix="/api/admin/content", tags=["admin-content"], dependencies=[Depends(get_current_admin)])


@router.get("/dashboard")
def dashboard_summary(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)) -> dict:
    return dashboard(db)


@router.get("/options", response_model=ContentOptionsResponse)
def content_options(db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)) -> ContentOptionsResponse:
    return ContentOptionsResponse(options=relation_options(db))


@router.post("/status/bulk")
def bulk_status(
    payload: AdminBulkStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, int]:
    return bulk_update_status(
        db,
        entity=payload.entity,
        ids=payload.ids,
        status_value=payload.status,
        access_state=payload.access_state,
        admin=admin,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/validation/{entity}", response_model=ValidationResult)
def validate_payload(
    entity: str,
    payload: AdminContentWriteRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ValidationResult:
    return validate_payload_entity(db, entity, payload.model_dump())


@router.get("/validation/{entity}/{item_id}", response_model=ValidationResult)
def validate_item(
    entity: str,
    item_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ValidationResult:
    return validate_current_entity(db, entity, item_id)


@router.get("/preview/{entity}/{item_id}", response_model=PreviewResponse)
def preview_item(
    entity: str,
    item_id: int,
    viewer_access: str = Query(default="free"),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> PreviewResponse:
    return build_preview(db, entity, item_id, viewer_access=viewer_access)


@router.get("/export/{entity}", response_model=ExportResponse)
def export_items(
    entity: str,
    format: str = Query(default="json"),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ExportResponse:
    return export_entity(db, entity, format_name=format)


@router.get("/templates/{entity}", response_model=ExportResponse)
def export_template(
    entity: str,
    format: str = Query(default="json"),
    admin: AdminUser = Depends(get_current_admin),
) -> ExportResponse:
    return template_export(entity, format_name=format)


@router.post("/import/{entity}", response_model=ImportResult)
def import_items(
    entity: str,
    payload: ImportRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> ImportResult:
    return import_entity(db, entity, payload, admin, getattr(request.state, "request_id", None))


@router.get("/{entity}", response_model=AdminContentListResponse)
def list_items(
    entity: str,
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
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> AdminContentListResponse:
    return AdminContentListResponse(
        **list_entities(
            db,
            entity,
            q=q,
            status_filter=status_filter,
            access_filter=access_filter,
            topic=topic,
            level=level,
            relation_id=relation_id,
            relation_field=relation_field,
            health_filter=health_filter,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    )


@router.post("/audio-assets/upload", response_model=dict)
def upload_audio_asset(
    file: UploadFile = File(...),
    audio_asset_id: int | None = Form(default=None),
    attachment_role: str = Form(default="general"),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
    settings: Settings = Depends(get_settings),
) -> dict:
    if audio_asset_id is not None:
        asset = db.get(AudioAsset, audio_asset_id)
        if not asset or asset.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio asset not found")
        row = replace_audio_asset_file(db=db, asset=asset, admin_id=admin.id, file=file, settings=settings)
    else:
        row = create_audio_asset_from_upload(db=db, admin_id=admin.id, file=file, settings=settings, attachment_role=attachment_role)
    db.commit()
    return get_entity(db, "audio-assets", row.id)


@router.post("/{entity}", response_model=dict)
def create_item(
    entity: str,
    payload: AdminContentWriteRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return create_entity(db, entity, payload.model_dump(), admin, getattr(request.state, "request_id", None))


@router.get("/{entity}/{item_id}", response_model=dict)
def get_item(entity: str, item_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)) -> dict:
    return get_entity(db, entity, item_id)


@router.put("/{entity}/{item_id}", response_model=dict)
def update_item(
    entity: str,
    item_id: int,
    payload: AdminContentWriteRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return update_entity(db, entity, item_id, payload.model_dump(), admin, getattr(request.state, "request_id", None))


@router.delete("/{entity}/{item_id}")
def delete_item(
    entity: str,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, bool]:
    return delete_entity(db, entity, item_id, admin, getattr(request.state, "request_id", None))


@router.post("/{entity}/{item_id}/duplicate", response_model=dict)
def duplicate_item(
    entity: str,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return duplicate_entity(db, entity, item_id, admin, getattr(request.state, "request_id", None))


@router.post("/{entity}/{item_id}/publish", response_model=dict)
def publish_item(
    entity: str,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return publish_entity(db, entity, item_id, admin, getattr(request.state, "request_id", None))


@router.post("/{entity}/{item_id}/unpublish", response_model=dict)
def unpublish_item(
    entity: str,
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict:
    return unpublish_entity(db, entity, item_id, admin, getattr(request.state, "request_id", None))


@router.post("/{entity}/reorder")
def reorder_items(
    entity: str,
    payload: AdminReorderRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
) -> dict[str, bool]:
    return reorder_entity(db, entity, payload.order, admin, getattr(request.state, "request_id", None))
