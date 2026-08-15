from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas import Pagination, VenueListOut, VenueOut
from app.core.feature_flags import FeatureFlags
from app.db.repositories.deal_repository import DealRepository
from app.db.repositories.venue_repository import VenueRepository
from app.services.presenters import present_deal, present_venue, utcnow


class VenueService:
    def __init__(self, db: Session, flags: FeatureFlags) -> None:
        self.flags = flags
        self.venues = VenueRepository(db)
        self.deals = DealRepository(db)

    def list_venues(
        self,
        *,
        city: str | None = None,
        neighborhood: str | None = None,
        category: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> VenueListOut:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        rows, total = self.venues.list_published(
            city=city,
            neighborhood=neighborhood,
            category=category,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        items = [present_venue(venue, []) for venue in rows]
        return VenueListOut(items=items, pagination=Pagination(page=page, page_size=page_size, total=total))

    def get_by_slug(self, slug: str, *, now: datetime | None = None) -> VenueOut:
        venue = self.venues.get_by_slug(slug)
        instant = now or utcnow()
        presented_deals = []
        for location in venue.locations:
            for deal in self.deals.list_for_location(location.id):
                presented_deals.append(
                    present_deal(
                        deal,
                        now=instant,
                        verification=self.deals.latest_verification(deal.id),
                        publication=deal.publications[0] if deal.publications else None,
                        flags=self.flags,
                    )
                )
        return present_venue(venue, presented_deals)

    def get(self, venue_id: UUID) -> VenueOut:
        venue = self.venues.get(venue_id)
        return present_venue(venue, [])
