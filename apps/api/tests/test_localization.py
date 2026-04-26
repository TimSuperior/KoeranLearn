from app.services.localization import normalize_language


def test_language_fallback() -> None:
    assert normalize_language("ru") == "ru"
    assert normalize_language("uz-Cyrl") == "uz"
    assert normalize_language(None) == "en"
