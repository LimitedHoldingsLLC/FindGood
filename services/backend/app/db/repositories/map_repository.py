"""Viewport queries against FindGood locations.

Google is not consulted here. We read stored coordinates and published
offers, then the service ranks one pin per location.
"""

from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Deal, Venue, VenueLocation
from app.db.models.enums import FreshnessStatus, LocationConfidence, PublicationState, RecordStatus, SightingState
from app.domain.map.bounds import ViewportBounds

HIDDEN_FRESHNESS = (
    FreshnessStatus.STALE,
    FreshnessStatus.EXPIRED,
    FreshnessStatus.VERIFICATION_FAILED,
)
HIDDEN_CONFIDENCE = (LocationConfidence.NEEDS_REVIEW, LocationConfidence.INVALID)


class MapRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def locations_in_bounds(
        self,
        bounds: ViewportBounds,
        *,
        offering_kind: str | None = None,
        deal_type: str | None = None,
        cuisine: str | None = None,
        price_level: int | None = None,
        q: str | None = None,
        weekday: int | None = None,
        vertical: str | None = None,
        limit: int = 200,
    ) -> list[VenueLocation]:
        stmt = (
            select(VenueLocation)
            .join(Venue)
            .where(
                VenueLocation.status == RecordStatus.PUBLISHED,
                Venue.status == RecordStatus.PUBLISHED,
                VenueLocation.location_confidence.notin_(HIDDEN_CONFIDENCE),
                VenueLocation.latitude.between(bounds.south, bounds.north),
            )
        )
        stmt = self._apply_lng(stmt, bounds)
        if vertical:
            stmt = stmt.where(Venue.vertical == vertical)
        if cuisine:
            stmt = stmt.where(or_(Venue.cuisines.contains([cuisine]), Venue.primary_category == cuisine))
        if price_level is not None:
            stmt = stmt.where(Venue.price_level == price_level)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Venue.name.ilike(pattern),
                    Venue.primary_category.ilike(pattern),
                    VenueLocation.neighborhood.ilike(pattern),
                    VenueLocation.city.ilike(pattern),
                )
            )
        stmt = stmt.options(
            selectinload(VenueLocation.venue).selectinload(Venue.provider_links),
            selectinload(VenueLocation.deals).selectinload(Deal.schedules),
            selectinload(VenueLocation.deals).selectinload(Deal.items),
        )
        rows = list(self.db.scalars(stmt.limit(limit)))
        visible: list[VenueLocation] = []
        for location in rows:
            deals = [
                deal
                for deal in location.deals
                if deal.status == RecordStatus.PUBLISHED
                and deal.publication_state == PublicationState.PUBLISHED
                and deal.freshness_status not in HIDDEN_FRESHNESS
                and deal.sighting_state not in {SightingState.EXPIRED, SightingState.REMOVED}
            ]
            if offering_kind and offering_kind != "both":
                deals = [deal for deal in deals if deal.offering_kind in {offering_kind, "both"}]
            if deal_type:
                deals = [deal for deal in deals if deal.deal_type == deal_type]
            if weekday is not None:
                deals = [deal for deal in deals if any(weekday in schedule.days_of_week for schedule in deal.schedules)]
            if not deals:
                continue
            location.deals = deals
            visible.append(location)
        return visible

    def get_location(self, location_id: UUID) -> VenueLocation | None:
        stmt = (
            select(VenueLocation)
            .options(selectinload(VenueLocation.venue).selectinload(Venue.provider_links))
            .where(VenueLocation.id == location_id)
        )
        return self.db.scalar(stmt)

    def quality_counts(self) -> dict[str, int]:
        from sqlalchemy import func

        total = int(self.db.scalar(select(func.count()).select_from(VenueLocation)) or 0)
        published = int(
            self.db.scalar(
                select(func.count())
                .select_from(VenueLocation)
                .join(Venue)
                .where(VenueLocation.status == RecordStatus.PUBLISHED, Venue.status == RecordStatus.PUBLISHED)
            )
            or 0
        )
        needs_review = int(
            self.db.scalar(
                select(func.count()).where(VenueLocation.location_confidence == LocationConfidence.NEEDS_REVIEW)
            )
            or 0
        )
        invalid = int(
            self.db.scalar(select(func.count()).where(VenueLocation.location_confidence == LocationConfidence.INVALID))
            or 0
        )
        missing_source = int(self.db.scalar(select(func.count()).where(VenueLocation.geocode_source.is_(None))) or 0)
        eligible = int(
            self.db.scalar(
                select(func.count())
                .select_from(VenueLocation)
                .join(Venue)
                .where(
                    VenueLocation.status == RecordStatus.PUBLISHED,
                    Venue.status == RecordStatus.PUBLISHED,
                    VenueLocation.location_confidence.notin_(HIDDEN_CONFIDENCE),
                )
            )
            or 0
        )
        return {
            "total_locations": total,
            "published_locations": published,
            "map_eligible": eligible,
            "map_ineligible": max(published - eligible, 0),
            "needs_review": needs_review,
            "invalid": invalid,
            "missing_geocode_source": missing_source,
        }

    def locations_needing_review(self, *, limit: int = 50) -> list[VenueLocation]:
        stmt = (
            select(VenueLocation)
            .options(selectinload(VenueLocation.venue))
            .where(VenueLocation.location_confidence.in_([LocationConfidence.NEEDS_REVIEW, LocationConfidence.INVALID]))
            .order_by(VenueLocation.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def locations_missing_geocode(self, *, limit: int = 20) -> list[VenueLocation]:
        stmt = (
            select(VenueLocation)
            .options(selectinload(VenueLocation.venue))
            .where(
                or_(VenueLocation.geocode_source.is_(None), VenueLocation.address_hash.is_(None)),
                VenueLocation.location_confidence != LocationConfidence.INVALID,
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def increment_demand(self, location_ids: list[UUID]) -> None:
        if not location_ids:
            return
        for location in self.db.scalars(
            select(VenueLocation).options(selectinload(VenueLocation.venue)).where(VenueLocation.id.in_(location_ids))
        ):
            location.map_demand_count = int(location.map_demand_count or 0) + 1
            venue = location.venue
            if venue is not None and location.map_demand_count % 10 == 0:
                from datetime import UTC, datetime, timedelta

                soon = datetime.now(UTC) + timedelta(hours=6)
                if venue.next_refresh_at is None or venue.next_refresh_at > soon:
                    venue.next_refresh_at = soon

    def _apply_lng(self, stmt: Select[tuple[VenueLocation]], bounds: ViewportBounds) -> Select[tuple[VenueLocation]]:
        if bounds.crosses_antimeridian:
            return stmt.where(
                or_(VenueLocation.longitude >= bounds.west, VenueLocation.longitude <= bounds.east)
            )
        return stmt.where(VenueLocation.longitude.between(bounds.west, bounds.east))
