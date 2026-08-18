from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlencode

import httpx


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float
    label: str | None = None
    accuracy: str | None = None
    source: str = "geocode"


class GeocodingAdapter(Protocol):
    def geocode(self, query: str) -> GeoPoint | None: ...


class NullGeocodingAdapter:
    """Map rendering never calls this. Missing coordinates wait for a background job."""

    def geocode(self, query: str) -> GeoPoint | None:
        return None


class GoogleGeocodingAdapter:
    """Official Geocoding API only. Not used while drawing the consumer map."""

    def __init__(self, api_key: str, *, timeout_seconds: float = 8) -> None:
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    def configured(self) -> bool:
        return bool(self.api_key)

    def geocode(self, query: str) -> GeoPoint | None:
        if not self.configured() or not query.strip():
            return None
        params = urlencode({"address": query, "key": self.api_key})
        url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"
        response = httpx.get(url, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            return None
        data = response.json()
        results = data.get("results") or []
        if not results:
            return None
        first = results[0]
        loc = (first.get("geometry") or {}).get("location") or {}
        lat = loc.get("lat")
        lng = loc.get("lng")
        if lat is None or lng is None:
            return None
        location_type = ((first.get("geometry") or {}).get("location_type") or "").casefold()
        accuracy = {
            "rooftop": "rooftop",
            "range_interpolated": "range_interpolated",
            "geometric_center": "geometric_center",
            "approximate": "approximate",
        }.get(location_type, "approximate")
        return GeoPoint(
            latitude=float(Decimal(str(lat))),
            longitude=float(Decimal(str(lng))),
            label=first.get("formatted_address"),
            accuracy=accuracy,
            source="address_geocode",
        )


def geocoding_adapter(*, api_key: str, enabled: bool) -> GeocodingAdapter:
    if enabled and api_key.strip():
        return GoogleGeocodingAdapter(api_key)
    return NullGeocodingAdapter()
