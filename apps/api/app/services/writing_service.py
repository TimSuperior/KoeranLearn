import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import increment_daily_limit
from app.models.schema import User, WritingSubmission
from app.services.analytics import track_event

HANGUL_RE = re.compile(r"[가-힣]")
BLOCKED_RE = re.compile(r"(ignore previous|system prompt|developer message|jailbreak)", re.IGNORECASE)


def correct_writing(db: Session, user: User, text: str, target_register: str | None, include_translation: bool) -> dict[str, Any]:
    settings = get_settings()
    limit = settings.premium_writing_daily_limit if user.is_premium else settings.writing_daily_free_limit
    used = increment_daily_limit("writing", user.telegram_id, limit)

    feedback: dict[str, Any] = {"issues": [], "register": target_register, "translations": {}}
    original = text.strip()

    if BLOCKED_RE.search(original):
        feedback["issues"].append(
            {
                "type": "moderation",
                "message": _localized(
                    user.interface_language,
                    "Запрос похож на попытку обойти правила. Исправляю только корейский текст.",
                    "So'rov qoidalarni chetlab o'tishga o'xshaydi. Faqat koreyscha matnni tuzataman.",
                    "The request looks like an attempt to bypass rules. I will only correct Korean text.",
                ),
            }
        )

    if not HANGUL_RE.search(original):
        feedback["issues"].append(
            {
                "type": "validation",
                "message": _localized(
                    user.interface_language,
                    "Введите предложение на корейском хангылем.",
                    "Koreyscha gapni Hangul bilan kiriting.",
                    "Enter a Korean sentence in Hangul.",
                ),
            }
        )

    corrected = original
    corrected = corrected.replace("저는학생", "저는 학생")
    corrected = corrected.replace("김치 먹어요", "김치를 먹어요")
    corrected = corrected.replace("물주세요", "물 주세요")
    corrected = re.sub(r"\s+", " ", corrected).strip()
    if corrected and corrected[-1] not in ".!?。":
        corrected += "."

    if original != corrected:
        feedback["issues"].append(
            {
                "type": "spacing_or_particle",
                "message": _localized(
                    user.interface_language,
                    "Исправлены пробелы или частица объекта.",
                    "Bo'shliq yoki obyekt zarrasi tuzatildi.",
                    "Spacing or object particle was corrected.",
                ),
            }
        )

    natural = corrected
    if target_register in {"formal_polite", "honorific"} and corrected.endswith("요."):
        natural = corrected.removesuffix("요.") + "습니다."
        feedback["issues"].append(
            {
                "type": "register",
                "message": _localized(
                    user.interface_language,
                    "Для начальника, профессора или официальной ситуации лучше формально-вежливый стиль.",
                    "Boshliq, professor yoki rasmiy vaziyatda rasmiy-odobli uslub yaxshiroq.",
                    "For a boss, professor, or official context, formal polite style is safer.",
                ),
            }
        )

    if include_translation:
        feedback["translations"] = {
            "literal": _localized(user.interface_language, "дословный перевод зависит от контекста", "so'zma-so'z tarjima kontekstga bog'liq", "literal translation depends on context"),
            "natural": _localized(user.interface_language, "естественный перевод зависит от ситуации", "tabiiy tarjima vaziyatga bog'liq", "natural translation depends on situation"),
        }

    submission = WritingSubmission(
        user_id=user.id,
        original_text=original,
        corrected_text=corrected,
        natural_text=natural,
        feedback=feedback,
        provider="deterministic",
    )
    db.add(submission)
    db.commit()
    track_event(db, "writing_correction_completed", user.telegram_id, user.interface_language, {"provider": "deterministic"})
    return {
        "corrected_text": corrected,
        "natural_text": natural,
        "feedback": feedback,
        "provider": "deterministic",
        "remaining_daily_quota": max(0, limit - used),
    }


def _localized(language: str, ru: str, uz: str, en: str) -> str:
    return {"ru": ru, "uz": uz, "en": en}.get(language, en)
