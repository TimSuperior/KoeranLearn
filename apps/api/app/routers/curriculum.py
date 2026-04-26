from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload

from app.core.db import get_db
from app.core.security import get_current_user_or_internal
from app.models.schema import ExampleSentence, GrammarPoint, LearningPath, Lesson, Scenario, User, Vocabulary
from app.schemas import GrammarDTO, GrammarDetailDTO, PathDTO, VocabularyDTO, VocabularyDetailDTO
from app.services.curriculum_service import get_guided_path
from app.services.learner_serializers import serialize_grammar, serialize_vocabulary
from app.services.premium import has_active_subscription, require_content_access
from app.core.config import get_settings

router = APIRouter(prefix="/api", tags=["curriculum"])


@router.get("/paths", response_model=list[PathDTO])
def paths(db: Session = Depends(get_db)) -> list[LearningPath]:
    path = get_guided_path(db)
    return [path] if path else []


@router.get("/grammar", response_model=list[GrammarDTO])
def grammar_list(
    language: str = Query(default="en"),
    topic: str | None = None,
    include_premium: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
) -> list[dict]:
    query = db.query(GrammarPoint)
    query = query.options(selectinload(GrammarPoint.example_sentence_records).selectinload(ExampleSentence.audio_assets))
    query = query.filter(GrammarPoint.is_deleted.is_(False), GrammarPoint.status == "published")
    query = query.filter(GrammarPoint.resolved_access_state.notin_(["hidden", "internal"]))
    if not (include_premium or has_active_subscription(db, user)):
        query = query.filter(GrammarPoint.is_premium.is_(False))
    if topic:
        query = query.filter(GrammarPoint.category == topic)
    settings = get_settings()
    return [serialize_grammar(db, user, settings, row, detail=False) for row in query.order_by(GrammarPoint.difficulty, GrammarPoint.id).all()]


@router.get("/grammar/{grammar_id}", response_model=GrammarDetailDTO)
def grammar_detail(grammar_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)) -> dict:
    row = (
        db.query(GrammarPoint)
        .options(
            selectinload(GrammarPoint.related_lessons).selectinload(Lesson.audio_assets),
            selectinload(GrammarPoint.related_scenarios).selectinload(Scenario.audio_assets),
            selectinload(GrammarPoint.example_sentence_records).selectinload(ExampleSentence.audio_assets),
        )
        .filter(GrammarPoint.id == grammar_id, GrammarPoint.is_deleted.is_(False), GrammarPoint.status == "published")
        .filter(GrammarPoint.resolved_access_state.notin_(["hidden", "internal"]))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grammar point not found")
    require_content_access(db, user, row.is_premium)
    return serialize_grammar(db, user, get_settings(), row, detail=True)


@router.get("/vocab", response_model=list[VocabularyDTO])
def vocab_list(
    language: str = Query(default="en"),
    topic: str | None = None,
    include_premium: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_or_internal),
) -> list[dict]:
    query = db.query(Vocabulary)
    query = query.options(selectinload(Vocabulary.audio_assets), selectinload(Vocabulary.example_sentence_records).selectinload(ExampleSentence.audio_assets))
    query = query.filter(Vocabulary.is_deleted.is_(False), Vocabulary.status == "published")
    query = query.filter(Vocabulary.resolved_access_state.notin_(["hidden", "internal"]))
    if not (include_premium or has_active_subscription(db, user)):
        query = query.filter(Vocabulary.is_premium.is_(False))
    if topic:
        query = query.filter(Vocabulary.topic == topic)
    settings = get_settings()
    return [serialize_vocabulary(db, user, settings, row, detail=False) for row in query.order_by(Vocabulary.topic, Vocabulary.id).limit(300).all()]


@router.get("/vocab/{vocab_id}", response_model=VocabularyDetailDTO)
def vocab_detail(vocab_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user_or_internal)) -> dict:
    row = (
        db.query(Vocabulary)
        .options(
            selectinload(Vocabulary.audio_assets),
            selectinload(Vocabulary.related_lessons).selectinload(Lesson.audio_assets),
            selectinload(Vocabulary.related_scenarios).selectinload(Scenario.audio_assets),
            selectinload(Vocabulary.example_sentence_records).selectinload(ExampleSentence.audio_assets),
        )
        .filter(Vocabulary.id == vocab_id, Vocabulary.is_deleted.is_(False), Vocabulary.status == "published")
        .filter(Vocabulary.resolved_access_state.notin_(["hidden", "internal"]))
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vocabulary item not found")
    require_content_access(db, user, row.is_premium)
    return serialize_vocabulary(db, user, get_settings(), row, detail=True)
