import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.models.schema import AdminUser, AuthSession, User, utcnow


def verify_telegram_webapp_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> dict[str, str]:
    if not init_data:
        raise ValueError("Missing init data")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash")

    auth_date = int(parsed.get("auth_date", "0") or "0")
    if auth_date and time.time() - auth_date > max_age_seconds:
        raise ValueError("Init data expired")

    data_check_string = "\n".join(f"{key}={parsed[key]}" for key in sorted(parsed))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Invalid Telegram init data hash")

    return parsed


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(value: str, secret_key: str) -> str:
    return hmac.new(secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_access_token(subject_type: str, subject_id: int, role: str, settings: Settings) -> tuple[str, int]:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": f"{subject_type}:{subject_id}",
        "typ": "access",
        "role": role,
        "exp": int(expires_at.timestamp()),
        "iat": int(time.time()),
    }
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body, settings.secret_key)}", settings.access_token_minutes * 60


def decode_access_token(token: str, settings: Settings) -> dict:
    try:
        body, signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    if not hmac.compare_digest(_sign(body, settings.secret_key), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    try:
        payload = json.loads(_b64decode(body))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc
    if payload.get("typ") != "access" or int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired access token")
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str, settings: Settings) -> str:
    return hmac.new(settings.secret_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def create_refresh_session(
    db: Session,
    *,
    subject_type: str,
    subject_id: int,
    role: str,
    settings: Settings,
    request: Request | None = None,
) -> tuple[AuthSession, str]:
    token = new_refresh_token()
    session = AuthSession(
        user_id=subject_id if subject_type == "user" else None,
        admin_user_id=subject_id if subject_type == "admin" else None,
        refresh_token_hash=hash_token(token, settings),
        subject_type=subject_type,
        role=role,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=request.client.host if request and request.client else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, token


def authenticate_refresh_token(db: Session, refresh_token: str, settings: Settings) -> AuthSession:
    session = db.query(AuthSession).filter(AuthSession.refresh_token_hash == hash_token(refresh_token, settings)).first()
    if not session or session.revoked_at is not None or session.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return session


def revoke_refresh_token(db: Session, refresh_token: str, settings: Settings) -> None:
    session = db.query(AuthSession).filter(AuthSession.refresh_token_hash == hash_token(refresh_token, settings)).first()
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    payload = decode_access_token(_bearer_token(authorization), settings)
    subject = str(payload.get("sub", ""))
    subject_type, _, subject_id = subject.partition(":")
    if subject_type != "user" or not subject_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User token required")
    user = db.get(User, int(subject_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_current_admin(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUser:
    payload = decode_access_token(_bearer_token(authorization), settings)
    subject = str(payload.get("sub", ""))
    subject_type, _, subject_id = subject.partition(":")
    if subject_type != "admin" or not subject_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin token required")
    admin = db.get(AdminUser, int(subject_id))
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive admin")
    return admin


def get_current_user_or_internal(
    authorization: str | None = Header(default=None),
    x_internal_token: str | None = Header(default=None),
    x_telegram_id: str | None = Header(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if x_internal_token and hmac.compare_digest(x_internal_token, settings.internal_service_token):
        if not x_telegram_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Telegram-Id required")
        user = db.query(User).filter(User.telegram_id == str(x_telegram_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user
    return get_current_user(authorization, db, settings)


def require_same_user_or_internal(user: User, requested_telegram_id: str | None, x_internal_token: str | None, settings: Settings) -> None:
    if x_internal_token and hmac.compare_digest(x_internal_token, settings.internal_service_token):
        return
    if requested_telegram_id and str(requested_telegram_id) != user.telegram_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, salt_raw, digest_raw = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = _b64decode(salt_raw)
    expected = _b64decode(digest_raw)
    calculated = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return hmac.compare_digest(calculated, expected)
