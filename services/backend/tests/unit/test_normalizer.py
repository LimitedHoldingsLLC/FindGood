from app.ingestion.normalizers.deal import (
    DealNormalizer,
    normalize_day,
    normalize_time,
    normalize_url,
)


def test_day_and_time_aliases() -> None:
    assert normalize_day("Monday") == 1
    assert normalize_day("sun") == 7
    assert normalize_time("3 PM") == "15:00"
    assert normalize_time("9 PM") == "21:00"
    assert normalize_time("close") == "close"


def test_url_normalization() -> None:
    assert normalize_url("HTTPS://HarborAndRye.example/") == "https://harborandrye.example"


def test_deal_payload_normalization() -> None:
    payload = DealNormalizer().normalize(
        {
            "venue": {"name": "  Harbor & Rye  ", "website": "https://HarborAndRye.example/"},
            "title": "  Weekday Harbor Hour ",
            "deal_type": "Happy Hour",
            "offering_kind": "BOTH",
            "schedules": [{"days": ["monday", "friday"], "start": "3 PM", "end": "6 PM"}],
            "items": [{"name": "Burger", "normal_price": "$18.00", "deal_price": "$10"}],
        }
    )
    assert payload["title"] == "Weekday Harbor Hour"
    assert payload["deal_type"] == "happy_hour"
    assert payload["schedules"][0]["days_of_week"] == [1, 5]
    assert payload["schedules"][0]["start_time"] == "15:00"
    assert payload["items"][0]["deal_price"] == "10.00"
