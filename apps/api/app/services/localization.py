from functools import lru_cache

from sqlalchemy.orm import Session

from app.models.schema import LocalizationEntry
from app.services.localization_catalog import catalog_bundle, catalog_text, iter_catalog_rows

SUPPORTED_LANGUAGES = ("ru", "uz", "en")
DEFAULT_LANGUAGE = "en"


def normalize_language(language: str | None) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    language = language.lower()
    if language.startswith("ru"):
        return "ru"
    if language.startswith("uz"):
        return "uz"
    if language.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


@lru_cache(maxsize=512)
def _cache_key(namespace: str, language: str) -> tuple[str, str]:
    return namespace, language


class LocalizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bundle(self, namespace: str, language: str) -> dict[str, str]:
        language = normalize_language(language)
        values = catalog_bundle(namespace, language)
        entries = (
            self.db.query(LocalizationEntry)
            .filter(
                LocalizationEntry.namespace == namespace,
                LocalizationEntry.language.in_([language, DEFAULT_LANGUAGE]),
                LocalizationEntry.is_deleted.is_(False),
                LocalizationEntry.status == "published",
            )
            .all()
        )
        for entry in entries:
            if entry.language == DEFAULT_LANGUAGE:
                values[entry.key] = entry.value
        for entry in entries:
            if entry.language == language:
                values[entry.key] = entry.value
        return values

    def text(self, namespace: str, key: str, language: str, fallback: str | None = None) -> str:
        language = normalize_language(language)
        entry = (
            self.db.query(LocalizationEntry)
            .filter(
                LocalizationEntry.namespace == namespace,
                LocalizationEntry.key == key,
                LocalizationEntry.language == language,
                LocalizationEntry.is_deleted.is_(False),
                LocalizationEntry.status == "published",
            )
            .first()
        )
        if entry:
            return entry.value
        if language != DEFAULT_LANGUAGE:
            entry = (
                self.db.query(LocalizationEntry)
                .filter(
                    LocalizationEntry.namespace == namespace,
                    LocalizationEntry.key == key,
                    LocalizationEntry.language == DEFAULT_LANGUAGE,
                    LocalizationEntry.is_deleted.is_(False),
                    LocalizationEntry.status == "published",
                )
                .first()
            )
            if entry:
                return entry.value
        return catalog_text(namespace, key, language, fallback=fallback)


def missing_keys(db: Session, namespace: str | None = None) -> list[dict[str, str]]:
    query = db.query(LocalizationEntry).filter(LocalizationEntry.is_deleted.is_(False))
    if namespace:
        query = query.filter(LocalizationEntry.namespace == namespace)
    rows = query.all()
    by_key: dict[tuple[str, str], set[str]] = {}
    for entry_namespace, key, language in iter_catalog_rows(namespace):
        by_key.setdefault((entry_namespace, key), set()).add(language)
    for row in rows:
        by_key.setdefault((row.namespace, row.key), set()).add(row.language)
    missing: list[dict[str, str]] = []
    for (entry_namespace, key), languages in sorted(by_key.items()):
        for language in SUPPORTED_LANGUAGES:
            if language not in languages:
                missing.append({"namespace": entry_namespace, "key": key, "language": language})
    return missing
