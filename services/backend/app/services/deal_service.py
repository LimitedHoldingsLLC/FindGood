from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas import DealListOut, DealOut, Pagination
from app.core.feature_flags import FeatureFlags
from app.db.models import Source
from app.db.repositories.deal_repository import DealRepository
from app.domain.schedules.engine import AvailabilityStatus, ScheduleWindow
from app.domain.schedules.windows import deal_matches_time_filter
from app.domain.taxonomy.discovery import TimeBucket
from app.domain.taxonomy.verticals import resolve_consumer_vertical
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
        vertical: str | None = None,
        max_price: Decimal | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        radius_km: float | None = None,
        active_now: bool | None = None,
        q: str | None = None,
        cuisine: str | None = None,
        price_level: int | None = None,
        drink_kind: str | None = None,
        accepts_reservations: bool | None = None,
        feature: str | None = None,
        when: TimeBucket | None = None,
        weekday: int | None = None,
        page: int = 1,
        page_size: int = 20,
        now: datetime | None = None,
    ) -> DealListOut:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        fetch_size = page_size
        offset = (page - 1) * page_size
        # Over-fetch when filtering in the domain layer (schedule math, happening-now).
        if active_now or when:
            fetch_size = 100
            offset = 0
        rows, total = self.deals.list_published(
            city=city,
            neighborhood=neighborhood,
            category=category,
            offering_kind=offering_kind,
            deal_type=deal_type,
            vertical=resolve_consumer_vertical(vertical),
            max_price=max_price,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            q=q,
            cuisine=cuisine,
            price_level=price_level,
            drink_kind=drink_kind,
            accepts_reservations=accepts_reservations,
            feature=feature,
            weekday=weekday,
            offset=offset,
            limit=fetch_size,
        )
        if when:
            rows = [row for row in rows if deal_matches_time_filter(_windows(row), when=when, weekday=weekday)]
            total = len(rows)
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
        elif when:
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


def _windows(deal) -> list[ScheduleWindow]:
    return [
        ScheduleWindow(
            days_of_week=frozenset(schedule.days_of_week),
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            ends_at_close=schedule.ends_at_close,
            valid_from=schedule.valid_from,
            valid_until=schedule.valid_until,
        )
        for schedule in deal.schedules
    ]


def _source_from_publication(db: Session, publication) -> Source | None:
    if publication is None or publication.source_id is None:
        return None
    return db.get(Source, publication.source_id)
