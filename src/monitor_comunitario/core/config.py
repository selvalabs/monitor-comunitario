from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_timezone: str = "America/Sao_Paulo"
    database_url: str = "sqlite:///./data/monitor_comunitario.db"
    admin_api_key: str = ""

    celesc_outages_url: str = "https://www.celesc.com.br/avisos-de-desligamentos"
    scraper_headless: bool = True
    scraper_timeout_ms: int = 30_000
    snapshot_dir: str = "./snapshots"

    scheduler_enabled: bool = True
    scheduler_hour: int = 6
    scheduler_minute: int = 0

    notification_provider: str = "app"

    evolution_base_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = ""
    evolution_enabled: bool = False

    hermes_telegram_enabled: bool = False
    hermes_telegram_bot_token: str = ""
    hermes_telegram_chat_id: str = ""
    hermes_telegram_api_base_url: str = "https://api.telegram.org"

    ads_enabled: bool = False
    ads_provider: str = "placeholder"
    adsense_client_id: str = ""
    adsense_default_slot: str = ""

    analytics_enabled: bool = False
    analytics_provider: str = "none"
    google_analytics_id: str = ""

    consent_required: bool = True
    consent_version: str = "2026-06-16-v1"

def validate_runtime_settings(settings: Settings) -> None:
    """Reject configuration values that would make a production deploy unsafe."""
    if settings.app_env.lower() != "production":
        return

    database_url = settings.database_url.lower()
    admin_api_key = settings.admin_api_key

    if database_url.startswith("sqlite"):
        raise ValueError("production requires a PostgreSQL database")
    if len(admin_api_key) < 32:
        raise ValueError("production requires an admin API key with at least 32 characters")
    if admin_api_key.lower() in {"change-me-local-admin-key", "change-me"}:
        raise ValueError("production rejects placeholder admin API keys")
    if "monitor:monitor@" in database_url:
        raise ValueError("production rejects example database credentials")


@lru_cache
def get_settings() -> Settings:
    """Cache settings so every module receives the same configuration instance."""
    return Settings()
