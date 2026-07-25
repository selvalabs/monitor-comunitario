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


@lru_cache
def get_settings() -> Settings:
    """Cache settings so every module receives the same configuration instance."""
    return Settings()
