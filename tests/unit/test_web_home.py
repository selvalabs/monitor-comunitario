from fastapi.testclient import TestClient

from monitor_comunitario.api.main import app


def test_home_page_returns_public_frontend() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Monitor Comunitário Celesc" in response.text
    assert "Espaço para anúncio local" in response.text
    assert "Política de Privacidade" in response.text
    assert "accept_legal_terms" in response.text
    assert 'id="email"' in response.text
    assert "email-verification-panel" in response.text
    assert "consent-banner" in response.text
    assert "theme-selector" in response.text
    assert "language-selector" in response.text
    assert "/static/preferences.js" in response.text


def test_home_page_emphasizes_registration_and_member_access_paths() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'class="path-panel path-panel-primary"' in response.text
    assert 'class="path-panel path-panel-secondary"' in response.text
    assert "Cadastre seu endereço" in response.text
    assert "Entre com seu telefone e código de acesso" in response.text
    assert "Saiba sobre desligamentos programados perto de você." in response.text
    assert "Confirme seu e-mail" in response.text
    assert "cruzamento com bairro e rua" not in response.text
    assert "consulta por ID" not in response.text
    assert "Use este código com seu telefone" in response.text
    assert "Usar apenas o necessário" in response.text
    assert "access-code-panel" in response.text


def test_public_javascript_preserves_registration_and_access_code_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'fetch("/users"' in response.text
    assert "copyAccessCode" in response.text
    assert "pending_email_verification" in response.text
    assert "/users/verify-email" in response.text
    assert "accessCodePanel.focus()" in response.text
    assert "Aceitar opcionais" in response.text


def test_static_stylesheet_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/static/styles.css")

    assert response.status_code == 200
    assert "--accent" in response.text


def test_preferences_javascript_supports_global_theme_selector() -> None:
    with TestClient(app) as client:
        response = client.get("/static/preferences.js")

    assert response.status_code == 200
    assert "monitor-comunitario:theme" in response.text
    assert "prefers-color-scheme: dark" in response.text
    assert "applyTheme" in response.text
    assert "theme-selector" in response.text


def test_preferences_javascript_supports_lightweight_language_selector() -> None:
    with TestClient(app) as client:
        response = client.get("/static/preferences.js")

    assert response.status_code == 200
    assert "monitor-comunitario:language" in response.text
    assert "language-selector" in response.text
    assert "applyLanguage" in response.text
    assert "pt:" in response.text
    assert "en:" in response.text
    assert "es:" in response.text
    assert "zh:" in response.text
    assert "fr:" in response.text
    assert "data-i18n" in response.text


def test_public_config_is_served_without_secret_values() -> None:
    with TestClient(app) as client:
        response = client.get("/public/config")

    assert response.status_code == 200

    body = response.json()

    assert "ads_enabled" in body
    assert "analytics_enabled" in body
    assert "consent_required" in body
    assert "consent_version" in body


def test_privacy_policy_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/privacidade")

    assert response.status_code == 200
    assert "Política de Privacidade" in response.text
    assert "LGPD" in response.text


def test_terms_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/termos")

    assert response.status_code == 200
    assert "Termos de Uso" in response.text


def test_cookie_policy_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/cookies")

    assert response.status_code == 200
    assert "Armazenamento Local" in response.text
    assert "ADS_ENABLED" in response.text
