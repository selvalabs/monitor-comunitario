from monitor_comunitario.cli import mask_database_url


def test_mask_database_url_keeps_sqlite_url() -> None:
    database_url = "sqlite:///./data/monitor_comunitario.db"

    assert mask_database_url(database_url) == database_url


def test_mask_database_url_masks_postgres_password() -> None:
    database_url = "postgresql://user:secret-password@example.supabase.co:5432/postgres"

    masked = mask_database_url(database_url)

    assert masked == "postgresql://user:***@example.supabase.co:5432/postgres"
    assert "secret-password" not in masked


def test_mask_database_url_masks_query_urls() -> None:
    database_url = "postgresql+psycopg://admin:secret@db.example.com/app?sslmode=require"

    masked = mask_database_url(database_url)

    assert masked == "postgresql+psycopg://admin:***@db.example.com/app?sslmode=require"
    assert "secret" not in masked


def test_mask_database_url_keeps_url_without_credentials() -> None:
    database_url = "postgresql://db.example.com:5432/app"

    assert mask_database_url(database_url) == database_url


def test_cli_hermes_process_command_runs(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from typer.testing import CliRunner

    from monitor_comunitario import cli

    class FakeSession:
        def __enter__(self):  # type: ignore[no-untyped-def]
            return self

        def __exit__(self, *_args):  # type: ignore[no-untyped-def]
            return None

    class FakeSummary:
        events_checked = 2
        events_processed = 2
        events_failed = 0

    monkeypatch.setattr(cli, "init_db", lambda: None)
    monkeypatch.setattr(cli, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(
        cli,
        "process_created_hermes_events",
        lambda session, limit: FakeSummary(),
    )

    result = CliRunner().invoke(cli.app, ["hermes-process", "--limit", "5"])

    assert result.exit_code == 0
    assert "Hermes local processing completed" in result.output
    assert "Events checked: 2" in result.output
    assert "Events processed: 2" in result.output
