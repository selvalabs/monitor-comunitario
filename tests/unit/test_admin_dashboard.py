from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app


def test_admin_dashboard_page_is_served_by_direct_url() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "Painel de diagnóstico" in response.text
    assert "ADMIN_API_KEY" in response.text
    assert "sessionStorage" in response.text
    assert "X-Admin-API-Key" in response.text
    assert "test-admin-key" not in response.text


def test_admin_dashboard_page_trailing_slash_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/admin/")

    assert response.status_code == 200
    assert "Painel de diagnóstico" in response.text


def test_admin_dashboard_javascript_is_served_without_hardcoded_key() -> None:
    with TestClient(app) as client:
        response = client.get("/static/admin.js")

    assert response.status_code == 200
    assert "sessionStorage" in response.text
    assert "X-Admin-API-Key" in response.text
    assert "/admin/diagnostics" in response.text
    assert "/admin/hermes/events?limit=10" in response.text
    assert "/admin/runs/manual" in response.text
    assert "test-admin-key" not in response.text
    assert "change-me" not in response.text


def test_admin_dashboard_has_hermes_events_table() -> None:
    with TestClient(app) as client:
        response = client.get("/admin")

    assert response.status_code == 200
    assert "Eventos Hermes" in response.text
    assert 'id="hermes-events-table-body"' in response.text


def test_admin_dashboard_stylesheet_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/static/admin.css")

    assert response.status_code == 200
    assert "--accent" in response.text
    assert ".status-grid" in response.text
