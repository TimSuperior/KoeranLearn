import json

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import (
    authenticate_refresh_token,
    create_access_token,
    create_refresh_session,
    get_current_admin,
    get_current_user,
    hash_password,
    revoke_refresh_token,
    verify_password,
    verify_telegram_webapp_init_data,
)
from app.models.schema import AdminUser, AuthSession, utcnow
from app.schemas import AdminLoginRequest, AdminMeDTO, AuthResponse, TelegramAuthRequest, TokenResponse, UserSummary
from app.services.curriculum_service import guided_path_progress
from app.services.user_service import get_or_create_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str, settings: Settings) -> None:
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.app_env != "local",
        samesite="lax",
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie("refresh_token", path="/api/auth", secure=settings.app_env != "local", samesite="lax")


def _auth_response(db: Session, request: Request, response: Response, user, settings: Settings) -> AuthResponse:
    access_token, expires_in = create_access_token("user", user.id, user.role, settings)
    _, refresh_token = create_refresh_session(
        db,
        subject_type="user",
        subject_id=user.id,
        role=user.role,
        settings=settings,
        request=request,
    )
    _set_refresh_cookie(response, refresh_token, settings)
    return AuthResponse(
        telegram_id=user.telegram_id,
        interface_language=user.interface_language,
        explanation_language=(user.preferences.explanation_language if user.preferences else user.interface_language),
        is_onboarded=user.is_onboarded,
        is_premium=user.is_premium,
        access_token=access_token,
        expires_in=expires_in,
    )


@router.post("/telegram-webapp", response_model=AuthResponse)
def telegram_webapp_auth(
    payload: TelegramAuthRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    if settings.app_env == "local" and payload.init_data.startswith("dev:"):
        telegram_id = payload.init_data.replace("dev:", "", 1) or "10001"
        user = get_or_create_user(db, telegram_id, first_name="Dev User", telegram_language_code="en")
        return _auth_response(db, request, response, user, settings)

    if not settings.telegram_bot_token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram bot token is not configured")

    try:
        parsed = verify_telegram_webapp_init_data(payload.init_data, settings.telegram_bot_token, settings.webapp_auth_max_age_seconds)
        tg_user = json.loads(parsed.get("user", "{}"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Telegram init data") from exc

    if not tg_user.get("id"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram user missing")

    user = get_or_create_user(
        db,
        str(tg_user["id"]),
        tg_user.get("username"),
        tg_user.get("first_name"),
        tg_user.get("language_code"),
    )
    return _auth_response(db, request, response, user, settings)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
    session = authenticate_refresh_token(db, refresh_token, settings)
    subject_id = session.user_id if session.subject_type == "user" else session.admin_user_id
    if not subject_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    access_token, expires_in = create_access_token(session.subject_type, subject_id, session.role, settings)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/logout")
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    if refresh_token:
        revoke_refresh_token(db, refresh_token, settings)
    _clear_refresh_cookie(response, settings)
    return {"ok": True}


@router.get("/me", response_model=UserSummary)
def me(user=Depends(get_current_user), db: Session = Depends(get_db)) -> UserSummary:
    _, progress = guided_path_progress(db, user, create=True)
    return UserSummary(
        telegram_id=user.telegram_id,
        interface_language=user.interface_language,
        explanation_language=(user.preferences.explanation_language if user.preferences else user.interface_language),
        is_onboarded=user.is_onboarded,
        is_premium=user.is_premium,
        xp=user.xp,
        streak_count=user.streak_count,
        current_lesson_id=progress.current_lesson_id if progress else None,
        current_path_id=progress.path_id if progress else None,
    )


def _ensure_bootstrap_admin(db: Session, settings: Settings) -> AdminUser:
    admin = db.query(AdminUser).filter(AdminUser.email == settings.admin_email).first()
    if admin:
        return admin
    if db.query(AdminUser).count() > 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
    admin = AdminUser(
        email=settings.admin_email,
        role="owner",
        password_hash=hash_password(settings.admin_password),
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@router.post("/admin/login", response_model=TokenResponse)
def admin_login(
    payload: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    admin = db.query(AdminUser).filter(AdminUser.email == payload.email).first()
    if not admin and payload.email == settings.admin_email:
        admin = _ensure_bootstrap_admin(db, settings)
    if not admin or not admin.is_active or not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    admin.last_login_at = utcnow()
    db.commit()
    access_token, expires_in = create_access_token("admin", admin.id, admin.role, settings)
    _, refresh_token = create_refresh_session(
        db,
        subject_type="admin",
        subject_id=admin.id,
        role=admin.role,
        settings=settings,
        request=request,
    )
    _set_refresh_cookie(response, refresh_token, settings)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/admin/me", response_model=AdminMeDTO)
def admin_me(admin: AdminUser = Depends(get_current_admin)) -> AdminMeDTO:
    return AdminMeDTO(id=admin.id, email=admin.email, role=admin.role)


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(get_current_admin)) -> dict[str, bool]:
    session = db.get(AuthSession, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session.revoked_at = utcnow()
    db.commit()
    return {"ok": True}
