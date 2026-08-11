import logging

from monitor_comunitario.notifications.telegram_bot import (
    _chunks,
    log_telegram_bot_failure,
    parse_allowed_user_ids,
)


def test_parse_allowed_user_ids_ignores_invalid_values() -> None:
    assert parse_allowed_user_ids("123, 456, nope, -7") == frozenset({123, 456})


def test_chunks_preserves_a_single_short_message() -> None:
    assert _chunks(["status", "active: 0"]) == ["status" + chr(10) + "active: 0"]


def test_telegram_failure_log_redacts_exception_content(caplog) -> None:
    token = "test-token-that-must-not-be-logged"
    error = RuntimeError(f"request failed: https://api.telegram.org/bot{token}/getUpdates")

    with caplog.at_level(logging.WARNING):
        log_telegram_bot_failure(error)

    assert token not in caplog.text
    assert "RuntimeError" in caplog.text
