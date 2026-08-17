from datetime import UTC
from decimal import Decimal

from app.ingestion.providers.google_places import GooglePlacesAdapter
from app.ingestion.providers.yelp import YelpAdapter


def test_google_place_normalizes_to_business() -> None:
    adapter = GooglePlacesAdapter(api_key="test", client=None)  # type: ignore[arg-type]
    place = {
        "id": "places/ChIJ123",
        "displayName": {"text": "Harbor & Rye"},
        "formattedAddress": "123 Sunset Blvd, Los Angeles, CA 90026",
        "location": {"latitude": 34.09, "longitude": -118.28},
        "nationalPhoneNumber": "(213) 555-0142",
        "websiteUri": "https://harborandrye.example",
        "types": ["restaurant", "bar"],
        "rating": 4.5,
        "userRatingCount": 120,
        "googleMapsUri": "https://maps.google.com/?cid=1",
        "addressComponents": [
            {"longText": "123", "types": ["street_number"]},
            {"longText": "Sunset Blvd", "types": ["route"]},
            {"longText": "Los Angeles", "types": ["locality"]},
            {"shortText": "CA", "longText": "California", "types": ["administrative_area_level_1"]},
            {"longText": "90026", "types": ["postal_code"]},
        ],
        "timeZone": {"id": "America/Los_Angeles"},
    }
    business = adapter._normalize(place)
    assert business is not None
    assert business.provider == "google_places"
    assert business.provider_business_id == "ChIJ123"
    assert business.name == "Harbor & Rye"
    assert business.location.city == "Los Angeles"
    assert business.location.latitude == Decimal("34.09")
    assert business.rating == Decimal("4.5")
    assert business.retrieved_at.tzinfo is UTC
    again = adapter._normalize(place)
    assert again is not None
    assert again.provider_business_id == business.provider_business_id


def test_yelp_business_normalizes_to_same_shape() -> None:
    adapter = YelpAdapter(api_key="test", client=None)  # type: ignore[arg-type]
    row = {
        "id": "abc123",
        "name": "Harbor & Rye",
        "url": "https://yelp.com/biz/harbor",
        "display_phone": "(213) 555-0142",
        "rating": 4.0,
        "review_count": 88,
        "categories": [{"alias": "bars", "title": "Bars"}],
        "coordinates": {"latitude": 34.09, "longitude": -118.28},
        "location": {
            "address1": "123 Sunset Blvd",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90026",
            "country": "US",
            "display_address": ["123 Sunset Blvd", "Los Angeles, CA 90026"],
        },
    }
    business = adapter._normalize(row)
    assert business is not None
    assert business.provider == "yelp"
    assert business.provider_business_id == "abc123"
    assert business.location.region == "CA"
    assert business.location.timezone == "America/Los_Angeles"
