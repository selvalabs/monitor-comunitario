from functools import lru_cache
from urllib.parse import parse_qs, urlsplit

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
    monitor_bot_api_key: str = ""
    redis_url: str = ""
    trusted_proxy_ips: str = ""
    rate_limit_register_limit: int = 5
    rate_limit_register_window_seconds: int = 600
    rate_limit_member_limit: int = 10
    rate_limit_member_window_seconds: int = 300
    member_session_ttl_seconds: int = 3600
    public_registration_enabled: bool = True
    email_verification_enabled: bool = False
    email_verification_ttl_seconds: int = 172800
    phone_confirmation_ttl_seconds: int = 172800
    email_verification_max_attempts: int = 5
    email_verification_resend_cooldown_seconds: int = 60
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True
    email_from: str = ""
    email_provider: str = "smtp"
    brevo_api_key: str = ""
    brevo_api_url: str = "https://api.brevo.com/v3/smtp/email"
    email_ingress_secret: str = ""
    email_ingress_allowed_recipients: str = "monitor@monitor-mail.soberania.cloud"
    email_ingress_max_raw_bytes: int = 10 * 1024 * 1024

    celesc_outages_url: str = "https://www.celesc.com.br/avisos-de-desligamentos"
    celesc_emergency_url: str = (
        "https://celgeoweb.celesc.com.br/json/mapa.js"
    )
    scraper_headless: bool = True
    scraper_timeout_ms: int = 30_000
    snapshot_dir: str = "./snapshots"

    scheduler_enabled: bool = True
    scheduler_hour: int = 6
    scheduler_minute: int = 0
    emergency_scheduler_interval_minutes: int = 5

    notification_provider: str = "app"

    evolution_base_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = ""
    evolution_enabled: bool = False
    hermes_callback_secret: str = ""
    hermes_event_api_secret: str = ""
    member_area_url: str = "https://monitorcomunitario.soberania.cloud/member"

    hermes_telegram_enabled: bool = False
    hermes_telegram_bot_token: str = ""
    hermes_telegram_chat_id: str = ""
    hermes_telegram_api_base_url: str = "https://api.telegram.org"
    monitor_bot_api_url: str = "http://monitor-comunitario-api:8000"

    monitor_telegram_enabled: bool = False
    monitor_telegram_bot_token: str = ""
    monitor_telegram_allowed_user_ids: str = ""
    monitor_telegram_api_base_url: str = "https://api.telegram.org"
    monitor_telegram_poll_timeout_seconds: int = 25

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
    ssl_modes = parse_qs(urlsplit(settings.database_url).query).get("sslmode", [])
    if not ssl_modes or ssl_modes[0].lower() not in {"require", "verify-ca", "verify-full"}:
        raise ValueError("production requires TLS for the database connection")
    if len(admin_api_key) < 32:
        raise ValueError("production requires an admin API key with at least 32 characters")
    if admin_api_key.lower() in {"change-me-local-admin-key", "change-me"}:
        raise ValueError("production rejects placeholder admin API keys")
    if "monitor:monitor@" in database_url:
        raise ValueError("production rejects example database credentials")
    if settings.monitor_telegram_enabled:
        if not settings.monitor_telegram_bot_token:
            raise ValueError("production requires the Monitor Telegram bot token")
        if not any(
            item.strip().isdigit()
            for item in settings.monitor_telegram_allowed_user_ids.split(",")
        ):
            raise ValueError("production requires an allowlist for Monitor Telegram users")
        if not settings.monitor_bot_api_key:
            raise ValueError("production requires the Monitor bot API key")
    if not settings.redis_url.startswith(("redis://", "rediss://")):
        raise ValueError("production requires a Redis URL for rate limiting")
    if (
        settings.public_registration_enabled
        and not settings.email_verification_enabled
    ):
        raise ValueError(
            "production requires email verification when public registration is enabled"
        )
    if settings.email_verification_enabled and not settings.email_from:
        raise ValueError("production requires a verified sender for email verification")
    if (
        settings.email_verification_enabled
        and settings.email_provider.lower() == "brevo"
        and not settings.brevo_api_key
    ):
        raise ValueError("production requires the Brevo API key for email verification")
    if (
        settings.email_verification_enabled
        and settings.email_provider.lower() == "smtp"
        and not settings.smtp_host
    ):
        raise ValueError("production requires SMTP settings for email verification")
    if (
        settings.email_verification_enabled
        and settings.email_provider.lower() not in {"smtp", "brevo"}
    ):
        raise ValueError("production requires a supported email provider")
    if settings.email_verification_enabled and not settings.hermes_callback_secret:
        raise ValueError("production requires Hermes callback settings for phone verification")
    if settings.email_verification_enabled and not settings.hermes_event_api_secret:
        raise ValueError("production requires Hermes event API settings")

@lru_cache
def get_settings() -> Settings:
    """Cache settings so every module receives the same configuration instance."""
    return Settings()
