"""Google Places (New) adapter.

Uses places.googleapis.com, not the older Place Details / Text Search REST
paths that Google has deprecated.

Licensing note: Google's terms typically restrict how Places data may be
cached, redistributed, and shown. We store a provider ID and identity fields
needed to operate FindGood, keep ratings/reviews in provider metadata (not as
FindGood's own scores), and do not send this data to the consumer frontend as
a Google clone. Treat extra_metadata as provider-owned and removable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.core.exceptions import ProviderAuthenticationError, ProviderError, ProviderNotConfigured, ProviderRateLimited
from app.domain.ingestion.schemas import NormalizedBusiness, NormalizedOffer
from app.ingestion.http import OutboundHttpClient
from app.ingestion.providers.base import ProviderSearchQuery
from app.ingestion.providers.normalize import location_from_parts

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_URL = "https://places.googleapis.com/v1/places/{place_id}"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.types",
        "places.rating",
        "places.userRatingCount",
        "places.regularOpeningHours",
        "places.googleMapsUri",
        "places.addressComponents",
        "places.timeZone",
        "places.utcOffsetMinutes",
    ]
)
DETAIL_MASK = FIELD_MASK.replace("places.", "")


class GooglePlacesAdapter:
    name = "google_places"

    def __init__(
        self,
        *,
        api_key: str,
        client: OutboundHttpClient,
        max_calls_per_run: int = 20,
        enabled: bool = True,
    ) -> None:
        self.api_key = api_key.strip()
        self.client = client
        self.max_calls_per_run = max_calls_per_run
        self.enabled = enabled
        self.calls_used = 0

    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)

    def search_businesses(self, query: ProviderSearchQuery) -> list[NormalizedBusiness]:
        self._ensure()
        text = query.text or "restaurants"
        if query.city:
            text = f"{text} in {query.city}"
        body: dict[str, Any] = {
            "textQuery": text,
            "includedType": "restaurant",
            "maxResultCount": min(max(query.max_results, 1), 20),
        }
        if query.latitude is not None and query.longitude is not None:
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": query.latitude, "longitude": query.longitude},
                    "radius": float(query.radius_meters),
                }
            }
        data = self._request("POST", SEARCH_URL, json_body=body, field_mask=FIELD_MASK)
        places = data.get("places") or []
        results: list[NormalizedBusiness] = []
        for place in places:
            normalized = self._normalize(place)
            if normalized:
                results.append(normalized)
        return results

    def fetch_business(self, provider_business_id: str) -> NormalizedBusiness | None:
        self._ensure()
        place_id = provider_business_id.removeprefix("places/")
        data = self._request("GET", PLACE_URL.format(place_id=place_id), field_mask=DETAIL_MASK)
        return self._normalize(data)

    def fetch_offers(self, provider_business_id: str) -> list[NormalizedOffer]:
        # Places does not provide happy-hour offers. Identity only.
        return []

    def _ensure(self) -> None:
        if not self.configured():
            raise ProviderNotConfigured(
                "Google Places is not configured. Set GOOGLE_PLACES_API_KEY to use this provider."
            )
        if self.calls_used >= self.max_calls_per_run:
            raise ProviderError("Google Places call budget for this run is exhausted")

    def _request(self, method: str, url: str, *, json_body: dict | None = None, field_mask: str) -> dict[str, Any]:
        self.calls_used += 1
        headers = {"X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": field_mask}
        if method == "POST":
            fetched = self.client.post(url, headers=headers, json_body=json_body, validate_url=True)
        else:
            fetched = self.client.get(url, headers=headers, validate_url=True)
        if fetched.http_status in {401, 403}:
            raise ProviderAuthenticationError("Google Places rejected the API key")
        if fetched.http_status == 429:
            raise ProviderRateLimited("Google Places rate limited this request")
        if fetched.http_status >= 400:
            raise ProviderError(f"Google Places HTTP {fetched.http_status}")
        import json

        return json.loads(fetched.content.decode("utf-8"))

    def _normalize(self, place: dict[str, Any]) -> NormalizedBusiness | None:
        place_id = (place.get("id") or "").removeprefix("places/")
        name = (place.get("displayName") or {}).get("text") or place.get("name")
        location_raw = place.get("location") or {}
        lat = location_raw.get("latitude")
        lng = location_raw.get("longitude")
        components = _address_components(place.get("addressComponents") or [])
        location = location_from_parts(
            address_line1=components.get("street"),
            city=components.get("city"),
            region=components.get("region"),
            postal_code=components.get("postal"),
            latitude=lat,
            longitude=lng,
            neighborhood=components.get("neighborhood"),
            timezone=(place.get("timeZone") or {}).get("id"),
            formatted=place.get("formattedAddress"),
        )
        if not place_id or not name or location is None:
            return None
        rating = place.get("rating")
        return NormalizedBusiness(
            provider="google_places",
            provider_business_id=place_id,
            name=str(name)[:200],
            phone=place.get("nationalPhoneNumber"),
            website_url=place.get("websiteUri"),
            categories=list(place.get("types") or [])[:12],
            location=location,
            google_maps_url=place.get("googleMapsUri"),
            provider_url=place.get("googleMapsUri"),
            rating=Decimal(str(rating)) if rating is not None else None,
            review_count=place.get("userRatingCount"),
            opening_hours=place.get("regularOpeningHours"),
            retrieved_at=datetime.now(UTC),
            extra={"raw_keys": sorted(place.keys())},
        )


def _address_components(components: list[dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    street_number = ""
    route = ""
    for item in components:
        types = set(item.get("types") or [])
        text = item.get("longText") or item.get("shortText") or ""
        short = item.get("shortText") or text
        if "street_number" in types:
            street_number = text
        elif "route" in types:
            route = text
        elif "locality" in types:
            out["city"] = text
        elif "administrative_area_level_1" in types:
            out["region"] = short
        elif "postal_code" in types:
            out["postal"] = text
        elif "neighborhood" in types:
            out["neighborhood"] = text
    street = " ".join(part for part in (street_number, route) if part).strip()
    if street:
        out["street"] = street
    return out
