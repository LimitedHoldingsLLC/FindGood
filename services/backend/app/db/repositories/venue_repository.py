from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import Venue, VenueLocation
from app.db.models.enums import RecordStatus


class VenueRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, venue_id: UUID) -> Venue:
        venue = self.db.get(Venue, venue_id)
        if venue is None:
            raise NotFoundError("Venue not found")
        return venue

    def get_by_slug(self, slug: str) -> Venue:
        stmt = select(Venue).options(selectinload(Venue.locations)).where(Venue.slug == slug)
        venue = self.db.scalar(stmt)
        if venue is None:
            raise NotFoundError("Venue not found")
        return venue

    def list_published(
        self,
        *,
        city: str | None = None,
        neighborhood: str | None = None,
        category: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Venue], int]:
        filters = [Venue.status == RecordStatus.PUBLISHED]
        stmt = select(Venue).options(selectinload(Venue.locations)).where(*filters)
        if city or neighborhood:
            stmt = stmt.join(VenueLocation)
            if city:
                stmt = stmt.where(VenueLocation.city.ilike(city))
            if neighborhood:
                stmt = stmt.where(VenueLocation.neighborhood.ilike(neighborhood))
            stmt = stmt.distinct()
        if category:
            stmt = stmt.where(Venue.primary_category == category)
        count_stmt = select(Venue.id)
        if city or neighborhood:
            count_stmt = count_stmt.join(VenueLocation)
            if city:
                count_stmt = count_stmt.where(VenueLocation.city.ilike(city))
            if neighborhood:
                count_stmt = count_stmt.where(VenueLocation.neighborhood.ilike(neighborhood))
        if category:
            count_stmt = count_stmt.where(Venue.primary_category == category)
        count_stmt = count_stmt.where(Venue.status == RecordStatus.PUBLISHED).distinct()
        total = len(list(self.db.scalars(count_stmt)))
        venues = list(self.db.scalars(stmt.order_by(Venue.name).offset(offset).limit(limit)))
        return venues, total

    def list_all(self) -> list[Venue]:
        stmt = select(Venue).options(selectinload(Venue.locations)).order_by(Venue.name)
        return list(self.db.scalars(stmt))

    def add(self, venue: Venue) -> Venue:
        self.db.add(venue)
        self.db.flush()
        return venue

    def get_location(self, location_id: UUID) -> VenueLocation:
        location = self.db.get(VenueLocation, location_id)
        if location is None:
            raise NotFoundError("Venue location not found")
        return location

    def add_location(self, location: VenueLocation) -> VenueLocation:
        self.db.add(location)
        self.db.flush()
        return location

    def find_location_for_venue_name(self, name: str) -> VenueLocation | None:
        stmt = select(VenueLocation).join(Venue).where(Venue.name.ilike(name)).limit(1)
        return self.db.scalar(stmt)
