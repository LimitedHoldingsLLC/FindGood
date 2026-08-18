"""Background coordinate enrichment. Never runs during a consumer map request."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.adapters.maps import GeocodingAdapter
from app.core.logging import get_logger
from app.db.models import VenueLocation
from app.db.models.enums import LocationConfidence
from app.db.repositories.map_repository import MapRepository
from app.domain.geo import address_hash

logger = get_logger("geocode")

_ACCURACY_CONFIDENCE = {
    "rooftop": LocationConfidence.HIGH_CONFIDENCE,
    "range_interpolated": LocationConfidence.HIGH_CONFIDENCE,
    "geometric_center": LocationConfidence.APPROXIMATE,
    "approximate": LocationConfidence.APPROXIMATE,
}


class GeocodeEnricher:
    def __init__(self, db: Session, adapter: GeocodingAdapter, *, max_calls: int) -> None:
        self.db = db
        self.adapter = adapter
        self.max_calls = max_calls
        self.calls = 0
        self.locations = MapRepository(db)

    def run(self) -> dict[str, int]:
        rows = self.locations.locations_missing_geocode(limit=self.max_calls)
        updated = 0
        skipped = 0
        for location in rows:
            if self.calls >= self.max_calls:
                break
            fingerprint = address_hash(
                location.address_line1, location.city, location.region, location.postal_code
            )
            if location.address_hash == fingerprint and location.geocode_source:
                skipped += 1
                continue
            query = f"{location.address_line1}, {location.city}, {location.region} {location.postal_code}"
            self.calls += 1
            point = self.adapter.geocode(query)
            now = datetime.now(UTC)
            location.address_hash = fingerprint
            location.geocoded_at = now
            if point is None:
                if not location.geocode_source:
                    location.location_confidence = LocationConfidence.NEEDS_REVIEW
                logger.info("geocode_miss", location_id=str(location.id))
                continue
            apply_geocode(location, point.latitude, point.longitude, point.source, point.accuracy)
            updated += 1
        self.db.flush()
        return {"updated": updated, "skipped": skipped, "calls": self.calls}


def apply_geocode(
    location: VenueLocation,
    latitude: float,
    longitude: float,
    source: str,
    accuracy: str | None,
    *,
    verified: bool = False,
) -> None:
    now = datetime.now(UTC)
    location.latitude = Decimal(str(latitude))
    location.longitude = Decimal(str(longitude))
    location.geocode_source = source
    location.geocode_accuracy = accuracy
    location.geocoded_at = now
    location.address_hash = address_hash(
        location.address_line1, location.city, location.region, location.postal_code
    )
    if verified:
        location.location_confidence = LocationConfidence.VERIFIED
        location.coordinates_verified_at = now
    else:
        location.location_confidence = _ACCURACY_CONFIDENCE.get(
            accuracy or "", LocationConfidence.APPROXIMATE
        )
