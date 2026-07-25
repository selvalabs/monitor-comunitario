from monitor_comunitario.core.config import Settings


def test_hermes_telegram_settings_default_disabled() -> None:
    settings = Settings()

    assert settings.hermes_telegram_enabled is False
    assert settings.hermes_telegram_bot_token == ""
    assert settings.hermes_telegram_chat_id == ""
    assert settings.hermes_telegram_api_base_url == "https://api.telegram.org"
