from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "sqlite:///./koreanlearn.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret"
    admin_token: str = "change-me"
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me"
    internal_service_token: str = "dev-internal-token"
    telegram_bot_token: str = ""
    media_dir: str = "./media"
    private_audio_dir: str = "./media-private/audio"
    audio_storage_backend: str = "local"
    audio_max_upload_bytes: int = 26214400
    audio_signed_url_ttl_seconds: int = 900
    audio_s3_endpoint: str = ""
    audio_s3_bucket: str = ""
    audio_s3_access_key: str = ""
    audio_s3_secret_key: str = ""
    audio_s3_region: str = "us-east-1"
    audio_s3_prefix: str = "premium-audio"
    webapp_auth_max_age_seconds: int = 86400
    posthog_api_key: str = ""
    posthog_host: str = "https://app.posthog.com"
    seed_demo_data: bool = True
    auto_create_tables: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    ai_provider: str = "disabled"
    ai_api_key: str = ""
    writing_daily_free_limit: int = 5
    premium_writing_daily_limit: int = 100
    log_level: str = "INFO"
    sentry_dsn: str = ""
    backup_dir: str = "/backups"
    backup_retention_days: int = 14
    s3_backup_endpoint: str = ""
    s3_backup_bucket: str = ""
    s3_backup_access_key: str = ""
    s3_backup_secret_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
