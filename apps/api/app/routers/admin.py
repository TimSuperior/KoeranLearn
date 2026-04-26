from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import get_current_admin
from app.models.schema import AnalyticsEvent, Exercise, Lesson, Scenario, User
from app.schemas import AdminLessonCreate, AdminLessonUpdate, LessonDTO

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "onboarded_users": db.query(User).filter(User.is_onboarded.is_(True)).count(),
        "lessons": db.query(Lesson).count(),
        "exercises": db.query(Exercise).count(),
        "scenarios": db.query(Scenario).count(),
        "events": db.query(AnalyticsEvent).count(),
    }


@router.get("/lessons", response_model=list[LessonDTO])
def lessons(db: Session = Depends(get_db)):
    return db.query(Lesson).options(selectinload(Lesson.blocks), selectinload(Lesson.assets), selectinload(Lesson.exercises).selectinload(Exercise.options)).order_by(Lesson.order_index).all()


@router.post("/lessons", response_model=LessonDTO)
def create_lesson(payload: AdminLessonCreate, db: Session = Depends(get_db)):
    lesson = Lesson(**payload.model_dump())
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return db.query(Lesson).options(selectinload(Lesson.blocks), selectinload(Lesson.assets), selectinload(Lesson.exercises).selectinload(Exercise.options)).filter(Lesson.id == lesson.id).first()


@router.put("/lessons/{lesson_id}", response_model=LessonDTO)
def update_lesson(lesson_id: int, payload: AdminLessonUpdate, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, key, value)
    db.commit()
    return db.query(Lesson).options(selectinload(Lesson.blocks), selectinload(Lesson.assets), selectinload(Lesson.exercises).selectinload(Exercise.options)).filter(Lesson.id == lesson.id).first()


@router.get("/analytics")
def analytics(db: Session = Depends(get_db)):
    event_counts = db.query(AnalyticsEvent.event_name, func.count(AnalyticsEvent.id)).group_by(AnalyticsEvent.event_name).all()
    difficult = db.query(AnalyticsEvent.audience_language, func.count(AnalyticsEvent.id)).group_by(AnalyticsEvent.audience_language).all()
    return {
        "event_counts": [{"event_name": name, "count": count} for name, count in event_counts],
        "events_by_language": [{"language": lang or "unknown", "count": count} for lang, count in difficult],
    }


@router.get("/content-preview/lesson/{lesson_id}", response_model=LessonDTO)
def lesson_preview(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).options(selectinload(Lesson.blocks), selectinload(Lesson.assets), selectinload(Lesson.exercises).selectinload(Exercise.options)).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return lesson


@router.post("/media/upload")
def upload_media(
    file: UploadFile = File(...),
    folder: str = Form(default="audio"),
    settings: Settings = Depends(get_settings),
):
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    safe_folder = folder.strip("/\\") or "audio"
    target_dir = Path(settings.media_dir) / safe_folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    target_path = target_dir / filename
    with target_path.open("wb") as handle:
        handle.write(file.file.read())
    return {
        "url": f"/media/{safe_folder}/{filename}",
        "filename": file.filename or filename,
        "content_type": file.content_type or "application/octet-stream",
    }
