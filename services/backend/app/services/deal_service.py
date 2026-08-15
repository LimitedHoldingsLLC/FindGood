from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas import DealListOut, DealOut, Pagination
from app.core.feature_flags import FeatureFlags
from app.db.models import Source
from app.db.repositories.deal_repository import DealRepository
from app.domain.schedules.engine import AvailabilityStatus
from app.services.presenters import present_deal, utcnow


class DealService:
    def __init__(self, db: Session, flags: FeatureFlags) -> None:
        self.db = db
        self.flags = flags
        self.deals = DealRepository(db)

    def list_deals(
        self,
        *,
        city: str | None = None,
        neighborhood: str | None = None,
        category: str | None = None,
        offering_kind: str | None = None,
        deal_type: str | None = None,
        max_price: Decimal | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        radius_km: float | None = None,
        active_now: bool | None = None,
        page: int = 1,
        page_size: int = 20,
        now: datetime | None = None,
    ) -> DealListOut:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        fetch_size = page_size
        offset = (page - 1) * page_size
        # Over-fetch when filtering active_now in the domain layer.
        if active_now:
            fetch_size = 100
            offset = 0
        rows, total = self.deals.list_published(
            city=city,
            neighborhood=neighborhood,
            category=category,
            offering_kind=offering_kind,
            deal_type=deal_type,
            max_price=max_price,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            offset=offset,
            limit=fetch_size,
        )
        instant = now or utcnow()
        verifications = self.deals.verifications_for_deals([row.id for row in rows])
        origin = (latitude, longitude) if latitude is not None and longitude is not None else None
        presented = [
            present_deal(
                row,
                now=instant,
                verification=verifications.get(row.id),
                publication=row.publications[0] if row.publications else None,
                source=_source_from_publication(self.db, row.publications[0] if row.publications else None),
                flags=self.flags,
                origin=origin,
            )
            for row in rows
        ]
        if active_now:
            presented = [deal for deal in presented if deal.availability.status == AvailabilityStatus.ACTIVE_NOW]
            total = len(presented)
            start = (page - 1) * page_size
            presented = presented[start : start + page_size]
        return DealListOut(
            items=presented,
            pagination=Pagination(page=page, page_size=page_size, total=total),
        )

    def get_deal(self, deal_id: UUID, *, now: datetime | None = None) -> DealOut:
        deal = self.deals.get(deal_id)
        verification = self.deals.latest_verification(deal.id)
        publication = deal.publications[0] if deal.publications else None
        return present_deal(
            deal,
            now=now or utcnow(),
            verification=verification,
            publication=publication,
            source=_source_from_publication(self.db, publication),
            flags=self.flags,
        )


def _source_from_publication(db: Session, publication) -> Source | None:
    if publication is None or publication.source_id is None:
        return None
    return db.get(Source, publication.source_id)
