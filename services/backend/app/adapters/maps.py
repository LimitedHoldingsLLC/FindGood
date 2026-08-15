from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeoPoint:
    latitude: float
    longitude: float
    label: str | None = None


class GeocodingAdapter(Protocol):
    def geocode(self, query: str) -> GeoPoint | None: ...


class NullGeocodingAdapter:
    """List-first MVP works without a map/geocoding vendor."""

    def geocode(self, query: str) -> GeoPoint | None:
        return None
