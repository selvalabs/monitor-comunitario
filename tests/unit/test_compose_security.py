from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_local_compose_binds_host_ports_to_loopback() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:5432:5432"' in compose
    assert '"127.0.0.1:8000:8000"' in compose


def test_supabase_compose_binds_api_to_loopback() -> None:
    compose = (ROOT / "docker-compose.supabase.yml").read_text(encoding="utf-8")

    assert '"127.0.0.1:8000:8000"' in compose


def test_production_compose_does_not_publish_api_port() -> None:
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")

    assert '"8000:8000"' not in compose
    assert "expose:" in compose
    assert '"8000"' in compose
