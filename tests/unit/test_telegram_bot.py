from monitor_comunitario.notifications.telegram_bot import parse_allowed_user_ids


def test_parse_allowed_user_ids_ignores_invalid_values() -> None:
    assert parse_allowed_user_ids("123, 456, nope, -7") == frozenset({123, 456})

