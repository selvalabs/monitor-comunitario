import pytest
from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app
from monitor_comunitario.core.config import Settings, validate_runtime_settings


def production_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "production",
        "database_url": "postgresql+psycopg://app:long-secret@db.example.com/app",
        "admin_api_key": "a" * 32,
        "redis_url": "redis://redis:6379/0",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_settings_accept_secure_configuration() -> None:
    validate_runtime_settings(production_settings())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_url", "sqlite:///./data/monitor.db"),
        ("admin_api_key", ""),
        ("admin_api_key", "short-key"),
        ("admin_api_key", "change-me-local-admin-key"),
        ("database_url", "postgresql+psycopg://monitor:monitor@postgres:5432/app"),
    ],
)
def test_production_settings_reject_insecure_values(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="production"):
        validate_runtime_settings(production_settings(**{field: value}))


def test_non_production_settings_keep_local_defaults_usable() -> None:
    validate_runtime_settings(Settings())


def test_security_headers_are_present() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["x-frame-options"] == "DENY"
