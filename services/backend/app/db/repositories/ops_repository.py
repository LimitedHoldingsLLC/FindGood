"""Admin/ops queries. Paginated lists and cheap aggregates for the control plane."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import (
    AdminAuditLog,
    CrawlDomain,
    Deal,
    ErrorEvent,
    ExtractionCandidate,
    IngestionRun,
    ProviderUsageDaily,
    ReviewItem,
    Venue,
    VenueLocation,
    VenueProviderLink,
)
from app.db.models.enums import CandidateReviewStatus, PublicationState, RecordStatus, ReviewItemStatus


class OpsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def count_venues(self, *, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(Venue)
        if since:
            stmt = stmt.where(Venue.created_at >= since)
        return int(self.db.scalar(stmt) or 0)

    def count_venues_by_status(self, status: str) -> int:
        return int(self.db.scalar(select(func.count()).where(Venue.status == status)) or 0)

    def count_deals(self, *, since: datetime | None = None, freshness: str | None = None) -> int:
        stmt = select(func.count()).select_from(Deal)
        if since:
            stmt = stmt.where(Deal.created_at >= since)
        if freshness:
            stmt = stmt.where(Deal.freshness_status == freshness)
        return int(self.db.scalar(stmt) or 0)

    def count_published_deals(self) -> int:
        return int(
            self.db.scalar(
                select(func.count()).where(
                    Deal.publication_state == PublicationState.PUBLISHED,
                    Deal.status == RecordStatus.PUBLISHED,
                )
            )
            or 0
        )

    def freshness_counts(self, model) -> dict[str, int]:
        rows = self.db.execute(select(model.freshness_status, func.count()).group_by(model.freshness_status))
        return {status or "unverified": int(count) for status, count in rows}

    def count_pending_review(self) -> int:
        return int(
            self.db.scalar(select(func.count()).where(ReviewItem.status == ReviewItemStatus.PENDING)) or 0
        ) + int(
            self.db.scalar(
                select(func.count()).where(ExtractionCandidate.review_status == CandidateReviewStatus.PENDING)
            )
            or 0
        )

    def count_runs(self, *, status: str | None = None, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(IngestionRun)
        if status:
            stmt = stmt.where(IngestionRun.status == status)
        if since:
            stmt = stmt.where(IngestionRun.created_at >= since)
        return int(self.db.scalar(stmt) or 0)

    def count_error_events(self, *, since: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(ErrorEvent)
        if since:
            stmt = stmt.where(ErrorEvent.created_at >= since)
        return int(self.db.scalar(stmt) or 0)

    def due_venues(self, now: datetime, limit: int) -> list[Venue]:
        stmt = (
            select(Venue)
            .where(Venue.next_refresh_at.is_not(None), Venue.next_refresh_at <= now)
            .order_by(Venue.next_refresh_at)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def due_deals(self, now: datetime, limit: int) -> list[Deal]:
        stmt = (
            select(Deal)
            .options(selectinload(Deal.schedules), selectinload(Deal.venue_location))
            .where(Deal.next_refresh_at.is_not(None), Deal.next_refresh_at <= now)
            .order_by(Deal.next_refresh_at)
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def deals_with_ended_schedules(self, today, limit: int) -> list[Deal]:
        from app.db.models import DealSchedule

        stmt = (
            select(Deal)
            .join(DealSchedule)
            .options(selectinload(Deal.schedules))
            .where(DealSchedule.valid_until.is_not(None), DealSchedule.valid_until < today)
            .distinct()
            .limit(limit)
        )
        return list(self.db.scalars(stmt))

    def paginate_venues(self, *, q: str | None, city: str | None, page: int, page_size: int):
        stmt = select(Venue).options(
            selectinload(Venue.locations),
            selectinload(Venue.provider_links),
        )
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(
                or_(
                    Venue.name.ilike(pattern),
                    Venue.phone.ilike(pattern),
                    Venue.website_url.ilike(pattern),
                )
            )
        if city:
            stmt = stmt.join(VenueLocation).where(VenueLocation.city.ilike(city)).distinct()
        return self._page(stmt, Venue.name, page, page_size)

    def paginate_deals(
        self,
        *,
        q: str | None,
        freshness: str | None,
        city: str | None,
        page: int,
        page_size: int,
    ):
        stmt = select(Deal).options(
            selectinload(Deal.schedules),
            selectinload(Deal.items),
            selectinload(Deal.publications),
            selectinload(Deal.venue_location).selectinload(VenueLocation.venue),
        )
        if q:
            stmt = stmt.where(Deal.title.ilike(f"%{q}%"))
        if freshness:
            stmt = stmt.where(Deal.freshness_status == freshness)
        if city:
            stmt = stmt.join(VenueLocation).where(VenueLocation.city.ilike(city))
        return self._page(stmt, Deal.title, page, page_size)

    def paginate_runs(
        self,
        *,
        provider: str | None,
        job_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ):
        stmt = select(IngestionRun)
        if provider:
            stmt = stmt.where(IngestionRun.provider == provider)
        if job_type:
            stmt = stmt.where(IngestionRun.job_type == job_type)
        if status:
            stmt = stmt.where(IngestionRun.status == status)
        return self._page(stmt, IngestionRun.created_at.desc(), page, page_size)

    def get_run(self, run_id: UUID) -> IngestionRun:
        run = self.db.get(IngestionRun, run_id)
        if run is None:
            raise NotFoundError("Ingestion run not found")
        return run

    def paginate_review(self, *, status: str | None, page: int, page_size: int):
        stmt = select(ReviewItem)
        if status:
            stmt = stmt.where(ReviewItem.status == status)
        return self._page(stmt, ReviewItem.created_at.desc(), page, page_size)

    def get_review(self, item_id: UUID) -> ReviewItem:
        item = self.db.get(ReviewItem, item_id)
        if item is None:
            raise NotFoundError("Review item not found")
        return item

    def grouped_errors(self, *, since: datetime, limit: int) -> list[dict]:
        stmt = (
            select(
                ErrorEvent.category,
                ErrorEvent.provider,
                func.count().label("count"),
                func.min(ErrorEvent.created_at).label("first_at"),
                func.max(ErrorEvent.created_at).label("latest_at"),
                func.max(ErrorEvent.message).label("example"),
            )
            .where(ErrorEvent.created_at >= since)
            .group_by(ErrorEvent.category, ErrorEvent.provider)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = self.db.execute(stmt)
        return [
            {
                "category": row.category,
                "provider": row.provider,
                "count": int(row._mapping["count"]),
                "first_at": row.first_at,
                "latest_at": row.latest_at,
                "example": row.example,
            }
            for row in rows
        ]

    def search(self, q: str, limit: int = 20) -> dict:
        pattern = f"%{q}%"
        venues = list(
            self.db.scalars(
                select(Venue).where(or_(Venue.name.ilike(pattern), Venue.phone.ilike(pattern))).limit(limit)
            )
        )
        deals = list(self.db.scalars(select(Deal).where(Deal.title.ilike(pattern)).limit(limit)))
        links = list(
            self.db.scalars(
                select(VenueProviderLink).where(VenueProviderLink.provider_business_id.ilike(pattern)).limit(limit)
            )
        )
        runs = []
        try:
            from uuid import UUID as _UUID

            run = self.db.get(IngestionRun, _UUID(q))
            if run:
                runs = [run]
        except Exception:
            runs = []
        return {"venues": venues, "deals": deals, "provider_links": links, "runs": runs}

    def provider_usage(self, provider: str, day) -> ProviderUsageDaily | None:
        return self.db.scalar(
            select(ProviderUsageDaily).where(ProviderUsageDaily.provider == provider, ProviderUsageDaily.day == day)
        )

    def latest_run(self, provider: str) -> IngestionRun | None:
        return self.db.scalar(
            select(IngestionRun)
            .where(IngestionRun.provider == provider)
            .order_by(IngestionRun.created_at.desc())
            .limit(1)
        )

    def crawl_domains(self, limit: int = 50) -> list[CrawlDomain]:
        return list(self.db.scalars(select(CrawlDomain).order_by(CrawlDomain.last_attempt_at.desc()).limit(limit)))

    def add_audit(self, log: AdminAuditLog) -> None:
        self.db.add(log)
        self.db.flush()

    def list_audit(self, limit: int = 100) -> list[AdminAuditLog]:
        return list(self.db.scalars(select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit)))

    def _page(self, stmt: Select, order, page: int, page_size: int):
        page = max(page, 1)
        page_size = min(max(page_size, 1), 50)
        count = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        rows = list(self.db.scalars(stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)))
        return rows, int(count), page, page_size
