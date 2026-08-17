from fastapi.testclient import TestClient


def test_ingestion_routes_require_admin(client: TestClient) -> None:
    assert client.get("/api/v1/admin/overview").status_code == 401
    assert client.post("/api/v1/admin/ingestion/crawl", json={"url": "https://example.com"}).status_code == 401


def test_admin_overview_with_key(client: TestClient) -> None:
    response = client.get("/api/v1/admin/overview", headers={"X-Admin-Key": "test-admin-key"})
    assert response.status_code == 200
    body = response.json()
    assert "freshness_health_percent" in body
    assert "total_businesses" in body


def test_crawl_rejects_localhost(client: TestClient) -> None:
    response = client.post(
        "/api/v1/admin/ingestion/crawl",
        headers={"X-Admin-Key": "test-admin-key"},
        json={"url": "http://127.0.0.1/menu", "sync": True},
    )
    assert response.status_code in {400, 409, 422}


def test_opentable_search_not_configured(client: TestClient) -> None:
    # There is no OpenTable search route that pretends to work.
    providers = client.get("/api/v1/admin/providers", headers={"X-Admin-Key": "test-admin-key"})
    assert providers.status_code == 200
    opentable = next(row for row in providers.json() if row["name"] == "opentable")
    assert opentable["configured"] is False
