from monitor_comunitario.notifications.telegram_bot import _chunks, parse_allowed_user_ids


def test_parse_allowed_user_ids_ignores_invalid_values() -> None:
    assert parse_allowed_user_ids("123, 456, nope, -7") == frozenset({123, 456})


def test_chunks_preserves_a_single_short_message() -> None:
    assert _chunks(["status", "active: 0"]) == ["status" + chr(10) + "active: 0"]
