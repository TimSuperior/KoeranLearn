from app.core.config import Settings
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_access_token_roundtrip() -> None:
    settings = Settings(secret_key="test-secret")

    token, expires_in = create_access_token("user", 42, "user", settings)
    payload = decode_access_token(token, settings)

    assert expires_in == settings.access_token_minutes * 60
    assert payload["sub"] == "user:42"
    assert payload["role"] == "user"


def test_password_hash_verification() -> None:
    password_hash = hash_password("correct horse")

    assert verify_password("correct horse", password_hash)
    assert not verify_password("wrong", password_hash)
