from decimal import Decimal
from math import cos, radians
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import Deal, DealItem, DealPublication, DealSchedule, Venue, VenueLocation
from app.db.models.enums import FreshnessStatus, PublicationState, RecordStatus, SightingState
from app.db.models.verification import Verification


class DealRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _eager(self, stmt: Select[tuple[Deal]]) -> Select[tuple[Deal]]:
        return stmt.options(
            selectinload(Deal.schedules),
            selectinload(Deal.items),
            selectinload(Deal.publications),
            selectinload(Deal.venue_location).selectinload(VenueLocation.venue),
        )

    def get(self, deal_id: UUID) -> Deal:
        stmt = self._eager(select(Deal).where(Deal.id == deal_id))
        deal = self.db.scalar(stmt)
        if deal is None:
            raise NotFoundError("Deal not found")
        return deal

    def list_published(
        self,
        *,
        city: str | None = None,
        neighborhood: str | None = None,
        category: str | None = None,
        offering_kind: str | None = None,
        deal_type: str | None = None,
        vertical: str | None = None,
        max_price: Decimal | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        radius_km: float | None = None,
        q: str | None = None,
        cuisine: str | None = None,
        price_level: int | None = None,
        drink_kind: str | None = None,
        accepts_reservations: bool | None = None,
        feature: str | None = None,
        weekday: int | None = None,
        min_rating: Decimal | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Deal], int]:
        stmt = (
            select(Deal)
            .join(VenueLocation)
            .join(Venue)
            .where(
                Deal.status == RecordStatus.PUBLISHED,
                Deal.publication_state == PublicationState.PUBLISHED,
                VenueLocation.status == RecordStatus.PUBLISHED,
                Venue.status == RecordStatus.PUBLISHED,
                Deal.freshness_status.notin_(
                    [FreshnessStatus.EXPIRED, FreshnessStatus.STALE, FreshnessStatus.VERIFICATION_FAILED]
                ),
                Deal.sighting_state.notin_([SightingState.EXPIRED, SightingState.REMOVED]),
            )
        )
        if city:
            stmt = stmt.where(VenueLocation.city.ilike(city))
        if neighborhood:
            stmt = stmt.where(VenueLocation.neighborhood.ilike(neighborhood))
        if category:
            stmt = stmt.where(Venue.primary_category == category)
        if offering_kind:
            if offering_kind == "both":
                pass
            else:
                stmt = stmt.where(Deal.offering_kind.in_([offering_kind, "both"]))
        if deal_type:
            stmt = stmt.where(Deal.deal_type == deal_type)
        if vertical:
            stmt = stmt.where(Deal.vertical == vertical)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Venue.name.ilike(pattern),
                    Deal.title.ilike(pattern),
                    Deal.description.ilike(pattern),
                    Venue.primary_category.ilike(pattern),
                    VenueLocation.neighborhood.ilike(pattern),
                )
            )
        if cuisine:
            stmt = stmt.where(or_(Venue.cuisines.contains([cuisine]), Venue.primary_category == cuisine))
        if price_level is not None:
            stmt = stmt.where(Venue.price_level == price_level)
        if drink_kind:
            stmt = stmt.where(Venue.drink_kinds.contains([drink_kind]))
        if accepts_reservations is True:
            stmt = stmt.where(Venue.accepts_reservations.is_(True))
        if feature:
            stmt = stmt.where(Venue.features.contains([feature]))
        if weekday is not None:
            weekday_deals = select(DealSchedule.deal_id).where(DealSchedule.days_of_week.contains([weekday]))
            stmt = stmt.where(Deal.id.in_(weekday_deals))
        if min_rating is not None:
            stmt = stmt.where(Venue.rating >= min_rating)
        if max_price is not None:
            stmt = stmt.where(Deal.id.in_(select(DealItem.deal_id).where(DealItem.deal_price <= max_price)))
        if latitude is not None and longitude is not None and radius_km:
            lat = float(latitude)
            lng = float(longitude)
            # Bounding box first; exact radius is applied in the service if needed.
            lat_delta = radius_km / 111.0
            lng_delta = radius_km / (111.0 * max(cos(radians(lat)), 0.2))
            stmt = stmt.where(
                VenueLocation.latitude.between(lat - lat_delta, lat + lat_delta),
                VenueLocation.longitude.between(lng - lng_delta, lng + lng_delta),
            )
        count = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = list(self.db.scalars(self._eager(stmt).order_by(Deal.title).offset(offset).limit(limit)))
        return rows, int(count)

    def list_for_location(self, location_id: UUID) -> list[Deal]:
        stmt = self._eager(
            select(Deal).where(
                Deal.venue_location_id == location_id,
                Deal.publication_state == PublicationState.PUBLISHED,
                Deal.status == RecordStatus.PUBLISHED,
                Deal.freshness_status.notin_(
                    [FreshnessStatus.EXPIRED, FreshnessStatus.STALE, FreshnessStatus.VERIFICATION_FAILED]
                ),
                Deal.sighting_state.notin_([SightingState.EXPIRED, SightingState.REMOVED]),
            )
        )
        return list(self.db.scalars(stmt.order_by(Deal.title)))

    def list_all(self) -> list[Deal]:
        return list(self.db.scalars(self._eager(select(Deal).order_by(Deal.title))))

    def add(self, deal: Deal) -> Deal:
        self.db.add(deal)
        self.db.flush()
        return deal

    def add_schedule(self, schedule: DealSchedule) -> DealSchedule:
        self.db.add(schedule)
        self.db.flush()
        return schedule

    def add_item(self, item: DealItem) -> DealItem:
        self.db.add(item)
        self.db.flush()
        return item

    def add_publication(self, publication: DealPublication) -> DealPublication:
        self.db.add(publication)
        self.db.flush()
        return publication

    def latest_verification(self, deal_id: UUID) -> Verification | None:
        stmt = (
            select(Verification)
            .where(Verification.subject_type == "deal", Verification.subject_id == deal_id)
            .order_by(Verification.verified_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def verifications_for_deals(self, deal_ids: list[UUID]) -> dict[UUID, Verification]:
        if not deal_ids:
            return {}
        stmt = (
            select(Verification)
            .where(Verification.subject_type == "deal", Verification.subject_id.in_(deal_ids))
            .order_by(Verification.verified_at.desc())
        )
        latest: dict[UUID, Verification] = {}
        for row in self.db.scalars(stmt):
            latest.setdefault(row.subject_id, row)
        return latest

    def list_all_for_location(self, location_id: UUID) -> list[Deal]:
        stmt = self._eager(select(Deal).where(Deal.venue_location_id == location_id).order_by(Deal.title))
        return list(self.db.scalars(stmt))
