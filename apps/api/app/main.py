import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.content.demo import seed_database
from app.core.config import get_settings
from app.core.db import SessionLocal, create_db_and_tables
from app.core.logging import RequestContextMiddleware, configure_logging
from app.routers import admin, admin_content, analytics, audio, auth, curriculum, learning, lessons, localization, onboarding, premium, reminders, review, scenarios, settings as settings_router, writing
from app.services.content_access import sync_all_content_access

settings = get_settings()
configure_logging(settings.log_level)
if settings.sentry_dsn:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.app_env, traces_sample_rate=0.05)

app = FastAPI(
    title="KoreanLearn Telegram Platform API",
    version="0.1.0",
    description="Curriculum-based Korean learning API for the Telegram bot.",
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.media_dir, exist_ok=True)
os.makedirs(settings.private_audio_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(curriculum.router)
app.include_router(learning.router)
app.include_router(lessons.router)
app.include_router(review.router)
app.include_router(scenarios.router)
app.include_router(writing.router)
app.include_router(reminders.router)
app.include_router(settings_router.router)
app.include_router(premium.router)
app.include_router(analytics.router)
app.include_router(localization.router)
app.include_router(audio.router)
app.include_router(admin.router)
app.include_router(admin_content.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("api.error").exception(
        "Unhandled API error",
        extra={"request_id": getattr(request.state, "request_id", None), "method": request.method, "path": request.url.path},
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": getattr(request.state, "request_id", None)})


@app.on_event("startup")
def startup() -> None:
    os.makedirs(settings.media_dir, exist_ok=True)
    os.makedirs(settings.private_audio_dir, exist_ok=True)
    if settings.auto_create_tables:
        create_db_and_tables()
    db = SessionLocal()
    try:
        if settings.seed_demo_data:
            seed_database(db)
        sync_all_content_access(db)
    finally:
        db.close()


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/health/ready", tags=["system"])
def ready() -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("select 1"))
    finally:
        db.close()
    return {"status": "ready", "database": "ok"}
