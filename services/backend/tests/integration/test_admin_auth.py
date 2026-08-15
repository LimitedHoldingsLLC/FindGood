import pytest
from fastapi.testclient import TestClient


@pytest.mark.usefixtures("client")
def test_admin_requires_key(client: TestClient) -> None:
    response = client.get("/api/v1/admin/venues")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert "traceback" not in body["error"]["message"].lower()


def test_admin_rejects_wrong_key(client: TestClient) -> None:
    response = client.get("/api/v1/admin/venues", headers={"X-Admin-Key": "nope"})
    assert response.status_code == 401


def test_admin_session_accepts_valid_key(client: TestClient) -> None:
    response = client.post("/api/v1/admin/session", json={"api_key": "test-admin-key"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
