from app.core.exceptions import ProviderNotConfigured
from app.ingestion.providers.opentable import REQUIRED_ACCESS, OpenTableAdapter


def test_opentable_is_not_configured_without_partner_access() -> None:
    adapter = OpenTableAdapter(api_key="pretend-key", enabled=True)
    assert adapter.configured() is False
    try:
        adapter.search_businesses(type("Q", (), {"text": "x", "city": "LA"})())  # type: ignore[arg-type]
        raise AssertionError("should have raised")
    except ProviderNotConfigured as exc:
        assert "partner" in str(exc).lower() or "authorized" in str(exc).lower()
        assert REQUIRED_ACCESS
