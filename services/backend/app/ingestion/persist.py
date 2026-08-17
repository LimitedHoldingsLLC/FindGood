"""Save a provider business into FindGood venues without creating duplicates.

A restaurant can appear in Google, Yelp, and on its own website. We look up
an existing provider ID first, then conservative identity matches, then create
a new venue only when we do not already know the place.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.ids import new_id
from app.core.logging import get_logger
from app.db.models import Source, Venue, VenueLocation, VenueProviderLink
from app.db.models.enums import RecordStatus, SourceType, TrustLevel
from app.domain.duplicates.matcher import SimpleDuplicateMatcher, VenueIdentity, classify_match
from app.domain.ingestion.schemas import NormalizedBusiness
from app.domain.venues.slug import slugify
from app.domain.verification.policy import next_refresh_after_success, windows_from_settings

logger = get_logger("persist")


class PersistResult:
    def __init__(self) -> None:
        self.venue: Venue | None = None
        self.created = False
        self.updated = False
        self.skipped = False
        self.needs_review = False
        self.match_reasons: list[str] = []


class BusinessPersister:
    def __init__(self, db: Session, settings: object) -> None:
        self.db = db
        self.settings = settings
        self.matcher = SimpleDuplicateMatcher()

    def upsert(self, business: NormalizedBusiness) -> PersistResult:
        result = PersistResult()
        now = datetime.now(UTC)
        existing_link = self.db.scalar(
            select(VenueProviderLink).where(
                VenueProviderLink.provider == business.provider,
                VenueProviderLink.provider_business_id == business.provider_business_id,
            )
        )
        if existing_link:
            venue = self.db.get(Venue, existing_link.venue_id)
            if venue is None:
                result.skipped = True
                return result
            self._touch_venue(venue, business, now)
            existing_link.last_seen_at = now
            existing_link.provider_url = business.provider_url or existing_link.provider_url
            existing_link.extra_metadata = _provider_meta(business)
            result.venue = venue
            result.updated = True
            return result

        identities = self._existing_identities()
        candidate = _as_identity(business)
        matches = self.matcher.match_venues(candidate, identities)
        best = matches[0] if matches else None
        decision = classify_match(best)
        if decision == "auto_merge" and best:
            venue = self.db.get(Venue, UUID(best.entity_id))
            if venue is None:
                decision = "new"
            else:
                self._touch_venue(venue, business, now)
                self._add_link(venue.id, business, now)
                result.venue = venue
                result.updated = True
                result.match_reasons = best.reasons
                logger.info("venue_merged", provider=business.provider, venue_id=str(venue.id), reasons=best.reasons)
                return result

        venue = self._create_venue(business, now)
        self._add_link(venue.id, business, now)
        result.venue = venue
        result.created = True
        if decision == "review" and best:
            result.needs_review = True
            result.match_reasons = best.reasons
        return result

    def _existing_identities(self) -> list[VenueIdentity]:
        stmt = select(Venue).options(selectinload(Venue.locations)).where(Venue.status != RecordStatus.ARCHIVED)
        identities: list[VenueIdentity] = []
        for venue in self.db.scalars(stmt):
            loc = venue.locations[0] if venue.locations else None
            identities.append(
                VenueIdentity(
                    id=str(venue.id),
                    name=venue.name,
                    city=loc.city if loc else "",
                    phone=venue.phone,
                    website_url=venue.website_url,
                    latitude=loc.latitude if loc else None,
                    longitude=loc.longitude if loc else None,
                    address_line1=loc.address_line1 if loc else None,
                )
            )
        return identities

    def _create_venue(self, business: NormalizedBusiness, now: datetime) -> Venue:
        slug = _unique_slug(self.db, slugify(business.name))
        loc = business.location
        windows = windows_from_settings(self.settings)
        venue = Venue(
            id=new_id(),
            name=business.name,
            slug=slug,
            website_url=business.website_url,
            phone=business.phone,
            primary_category=(business.categories[0] if business.categories else "restaurant")[:80],
            status=RecordStatus.PUBLISHED,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            next_refresh_at=next_refresh_after_success(kind="venue_identity", now=now, windows=windows),
            freshness_status="fresh",
        )
        self.db.add(venue)
        self.db.flush()
        self.db.add(
            VenueLocation(
                id=new_id(),
                venue_id=venue.id,
                address_line1=loc.address_line1,
                address_line2=loc.address_line2,
                city=loc.city,
                region=loc.region,
                postal_code=loc.postal_code,
                country=loc.country,
                neighborhood=loc.neighborhood,
                latitude=loc.latitude,
                longitude=loc.longitude,
                timezone=loc.timezone,
            )
        )
        if business.website_url:
            self._ensure_website_source(venue.id, business.website_url)
        self.db.flush()
        return venue

    def _touch_venue(self, venue: Venue, business: NormalizedBusiness, now: datetime) -> None:
        venue.last_seen_at = now
        if not venue.phone and business.phone:
            venue.phone = business.phone
        if not venue.website_url and business.website_url:
            venue.website_url = business.website_url
            self._ensure_website_source(venue.id, business.website_url)
        windows = windows_from_settings(self.settings)
        venue.next_refresh_at = next_refresh_after_success(kind="venue_identity", now=now, windows=windows)

    def _add_link(self, venue_id: UUID, business: NormalizedBusiness, now: datetime) -> None:
        self.db.add(
            VenueProviderLink(
                id=new_id(),
                venue_id=venue_id,
                provider=business.provider,
                provider_business_id=business.provider_business_id,
                provider_url=business.provider_url,
                first_seen_at=now,
                last_seen_at=now,
                extra_metadata=_provider_meta(business),
            )
        )
        self.db.flush()

    def _ensure_website_source(self, venue_id: UUID, url: str) -> None:
        identity = f"website:{url.rstrip('/')}"
        existing = self.db.scalar(select(Source).where(Source.canonical_identity == identity))
        if existing:
            return
        self.db.add(
            Source(
                id=new_id(),
                venue_id=venue_id,
                source_type=SourceType.RESTAURANT_WEBSITE,
                url=url,
                canonical_identity=identity,
                is_active=True,
                crawl_enabled=True,
                trust_level=TrustLevel.HIGH,
            )
        )


def _as_identity(business: NormalizedBusiness) -> VenueIdentity:
    loc = business.location
    return VenueIdentity(
        id="incoming",
        name=business.name,
        city=loc.city,
        phone=business.phone,
        website_url=business.website_url,
        latitude=loc.latitude,
        longitude=loc.longitude,
        address_line1=loc.address_line1,
    )


def _provider_meta(business: NormalizedBusiness) -> dict:
    # Ratings stay here, not on the public venue row, because provider terms
    # often restrict redistributing reviews as if they were FindGood's.
    return {
        "rating": str(business.rating) if business.rating is not None else None,
        "review_count": business.review_count,
        "categories": business.categories,
        "opening_hours": business.opening_hours,
        "retrieved_at": business.retrieved_at.isoformat(),
    }


def _unique_slug(db: Session, base: str) -> str:
    slug = base
    suffix = 2
    while db.scalar(select(Venue.id).where(Venue.slug == slug)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug
