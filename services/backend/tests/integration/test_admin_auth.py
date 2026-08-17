from fastapi.testclient import TestClient


def test_admin_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/admin/venues")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert "traceback" not in body["error"]["message"].lower()


def test_admin_rejects_wrong_key(client: TestClient) -> None:
    response = client.get("/api/v1/admin/venues", headers={"X-Admin-Key": "nope"})
    assert response.status_code == 401


def test_admin_rejects_wrong_password(client: TestClient) -> None:
    response = client.post("/api/v1/admin/session", json={"username": "admin", "password": "nope"})
    assert response.status_code == 401


def test_admin_session_issues_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/session",
        json={"username": "admin", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["subject"] == "admin"
    assert body["token"]
    assert body["expires_at"]


def test_admin_bearer_token_opens_admin_routes(client: TestClient) -> None:
    session = client.post(
        "/api/v1/admin/session",
        json={"username": "admin", "password": "test-admin-password"},
    )
    token = session.json()["token"]
    response = client.get("/api/v1/admin/venues", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_admin_api_key_still_works_for_machine_access(client: TestClient) -> None:
    response = client.get("/api/v1/admin/venues", headers={"X-Admin-Key": "test-admin-key"})
    assert response.status_code == 200
