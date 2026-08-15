from app.ingestion.extractors.demo import DemoExtractor
from app.ingestion.fetchers.demo import DemoFetcher
from app.ingestion.normalizers.deal import DealNormalizer
from app.ingestion.parsers.json_parser import JsonParser
from app.ingestion.validators.deal import DealValidator


def test_demo_fixture_round_trip() -> None:
    fetched = DemoFetcher().fetch("demo://nightbird-new-special", user_agent="test", timeout_seconds=1)
    parsed = JsonParser().parse(fetched)
    extracted = DemoExtractor().extract(parsed)
    assert extracted
    normalized = DealNormalizer().normalize(extracted[0].payload)
    errors = DealValidator().validate({**normalized, "confidence": extracted[0].confidence})
    assert errors == []
    assert normalized["title"] == "Midnight Negroni"
    assert normalized["schedules"][0]["ends_at_close"] is True
    assert normalized["items"][0]["deal_price"] == "8.00"


def test_demo_fetcher_does_not_accept_http() -> None:
    try:
        DemoFetcher().fetch("https://example.com", user_agent="test", timeout_seconds=1)
        raise AssertionError("should have failed")
    except ValueError:
        pass
