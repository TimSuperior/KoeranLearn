from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_current_admin
from app.models.schema import LocalizationEntry
from app.schemas import ContentEntityPayload, LocalizationEntryDTO
from app.services.localization import LocalizationService, missing_keys

router = APIRouter(prefix="/api/localization", tags=["localization"])


@router.get("/bundle")
def bundle(namespace: str = Query(default="web"), language: str = Query(default="en"), db: Session = Depends(get_db)) -> dict[str, str]:
    return LocalizationService(db).bundle(namespace, language)


@router.get("/missing", dependencies=[Depends(get_current_admin)])
def missing(namespace: str | None = None, db: Session = Depends(get_db)):
    return missing_keys(db, namespace)


@router.get("/entries", response_model=list[LocalizationEntryDTO], dependencies=[Depends(get_current_admin)])
def entries(
    namespace: str | None = None,
    language: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(LocalizationEntry).filter(LocalizationEntry.is_deleted.is_(False))
    if namespace:
        query = query.filter(LocalizationEntry.namespace == namespace)
    if language:
        query = query.filter(LocalizationEntry.language == language)
    if q:
        query = query.filter(LocalizationEntry.key.ilike(f"%{q}%"))
    return query.order_by(LocalizationEntry.namespace, LocalizationEntry.key, LocalizationEntry.language).limit(500).all()


@router.post("/entries", response_model=LocalizationEntryDTO, dependencies=[Depends(get_current_admin)])
def create_entry(payload: ContentEntityPayload, db: Session = Depends(get_db)):
    entry = LocalizationEntry(**payload.data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.put("/entries/{entry_id}", response_model=LocalizationEntryDTO, dependencies=[Depends(get_current_admin)])
def update_entry(entry_id: int, payload: ContentEntityPayload, db: Session = Depends(get_db)):
    entry = db.get(LocalizationEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Localization entry not found")
    for key, value in payload.data.items():
        setattr(entry, key, value)
    db.commit()
    db.refresh(entry)
    return entry
