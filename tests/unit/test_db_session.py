from monitor_comunitario.db import session


def test_postgres_pooler_disables_prepared_statements() -> None:
    assert session._connect_args("postgresql+psycopg://user:pass@host/db") == {
        "prepare_threshold": None,
    }


def test_sqlite_keeps_thread_option() -> None:
    assert session._connect_args("sqlite:///./data/test.db") == {
        "check_same_thread": False,
    }


def test_unknown_database_dialect_has_no_special_options() -> None:
    assert session._connect_args("mysql+pymysql://user:pass@host/db") == {}
