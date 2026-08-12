from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_dockerfile_declares_non_root_runtime_user_and_owned_runtime_dirs() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "groupadd" in dockerfile
    assert "useradd" in dockerfile
    assert "chown" in dockerfile
    assert "USER monitor" in dockerfile
    assert "monitor:monitor" in dockerfile


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

def test_production_compose_applies_edge_rate_limit_to_monitor_router() -> None:
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")

    assert (
        "traefik.http.routers.monitor-comunitario.middlewares="
        "monitor-comunitario-rate-limit@docker"
    ) in compose
    assert "traefik.http.middlewares.monitor-comunitario-rate-limit.ratelimit.average=30" in compose
    assert "traefik.http.middlewares.monitor-comunitario-rate-limit.ratelimit.burst=60" in compose
    assert "traefik.http.middlewares.monitor-comunitario-rate-limit.ratelimit.period=1m" in compose


def test_production_compose_keeps_internal_api_off_public_edge() -> None:
    compose = (ROOT / "docker-compose.production.yml").read_text(encoding="utf-8")

    internal_service = compose.split("  api-internal:", 1)[1].split("  cloudflared:", 1)[0]
    assert "monitor_comunitario.api.internal:app" in internal_service
    assert "ports:" not in internal_service
    assert "traefik." not in internal_service
    assert "monitor_internal" in internal_service
    assert "MONITOR_BOT_API_URL=http://api-internal:8000" in compose
