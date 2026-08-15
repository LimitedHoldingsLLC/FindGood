from app.db.seed import seed
from fastapi.testclient import TestClient


def _admin(client: TestClient, method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-Admin-Key"] = "test-admin-key"
    return getattr(client, method)(path, headers=headers, **kwargs)


def test_seed_and_consumer_deals(client: TestClient) -> None:
    seed()
    health = client.get("/health")
    assert health.status_code == 200
    deals = client.get("/api/v1/deals")
    assert deals.status_code == 200
    payload = deals.json()
    assert payload["pagination"]["total"] >= 1
    first = payload["items"][0]
    assert "availability" in first
    assert "verification" in first
    venue = client.get(f"/api/v1/venues/{first['venue']['slug']}")
    assert venue.status_code == 200


def test_ingestion_snapshot_candidate_publish_provenance(client: TestClient) -> None:
    seed()
    sources = _admin(client, "get", "/api/v1/admin/sources").json()
    demo = next(source for source in sources if source["url"] == "demo://nightbird-new-special")
    run = _admin(client, "post", f"/api/v1/admin/sources/{demo['id']}/refresh/sync")
    assert run.status_code == 200
    assert run.json()["status"] == "succeeded"
    assert run.json()["extracted_count"] >= 1

    snapshots = _admin(client, "get", f"/api/v1/admin/sources/{demo['id']}/snapshots").json()
    assert snapshots
    assert snapshots[0]["content_hash"]
    assert snapshots[0]["raw_content"]

    # Snapshots are created again on re-run; they are not overwritten.
    _admin(client, "post", f"/api/v1/admin/sources/{demo['id']}/refresh/sync")
    snapshots_again = _admin(client, "get", f"/api/v1/admin/sources/{demo['id']}/snapshots").json()
    assert len(snapshots_again) >= 2
    hashes = {row["content_hash"] for row in snapshots_again}
    assert len(hashes) == 1

    candidates = _admin(client, "get", "/api/v1/admin/candidates?review_status=pending").json()
    nightbird = next(row for row in candidates if row["normalized_payload"]["title"] == "Midnight Negroni")
    published = _admin(client, "post", f"/api/v1/admin/candidates/{nightbird['id']}/approve")
    assert published.status_code == 200
    deal = published.json()
    assert deal["title"] == "Midnight Negroni"
    assert deal["provenance"]["snapshot_id"] == nightbird["source_snapshot_id"]

    consumer = client.get(f"/api/v1/deals/{deal['id']}")
    assert consumer.status_code == 200
    assert consumer.json()["title"] == "Midnight Negroni"
