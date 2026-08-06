from fastapi.testclient import TestClient

ADMIN_API_KEY = "test-admin-key"

def admin_session_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/admin/session",
        headers={"X-Admin-API-Key": ADMIN_API_KEY},
    )
    assert response.status_code == 200
    csrf_token = client.cookies.get("monitor_admin_csrf")
    assert csrf_token
    return {"X-CSRF-Token": csrf_token}
