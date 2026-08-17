from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.api.schemas import (
    CandidateOut,
    CrawlRunOut,
    DealCreateIn,
    DealOut,
    DealUpdateIn,
    ItemCreateIn,
    LocationCreateIn,
    ScheduleCreateIn,
    SnapshotOut,
    SourceCreateIn,
    SourceOut,
    VenueCreateIn,
    VenueOut,
    VenueUpdateIn,
    VerifyIn,
)
from app.core.exceptions import ConflictError, ValidationFailed
from app.core.feature_flags import FeatureFlags
from app.core.ids import new_id
from app.db.models import (
    Deal,
    DealItem,
    DealPublication,
    DealSchedule,
    Source,
    Venue,
    VenueLocation,
)
from app.db.models.enums import SourceType, VerificationType
from app.db.models.verification import Verification
from app.db.repositories.deal_repository import DealRepository
from app.db.repositories.source_repository import SourceRepository
from app.db.repositories.venue_repository import VenueRepository
from app.db.repositories.verification_repository import VerificationRepository
from app.domain.deals.money import parse_money
from app.domain.venues.slug import slugify
from app.services.presenters import present_deal, present_venue, utcnow


class AdminService:
    def __init__(self, db: Session, flags: FeatureFlags) -> None:
        self.db = db
        self.flags = flags
        self.venues = VenueRepository(db)
        self.deals = DealRepository(db)
        self.sources = SourceRepository(db)
        self.verifications = VerificationRepository(db)

    def list_venues(self) -> list[VenueOut]:
        return [present_venue(venue, []) for venue in self.venues.list_all()]

    def create_venue(self, payload: VenueCreateIn) -> VenueOut:
        slug = _unique_slug(self.db, slugify(payload.name))
        venue = Venue(
            id=new_id(),
            name=payload.name,
            slug=slug,
            description=payload.description,
            website_url=payload.website_url,
            phone=payload.phone,
            primary_category=payload.primary_category,
            vertical=payload.vertical,
            status=payload.status,
        )
        self.venues.add(venue)
        return present_venue(venue, [])

    def update_venue(self, venue_id: UUID, payload: VenueUpdateIn) -> VenueOut:
        venue = self.venues.get(venue_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(venue, field, value)
        self.db.flush()
        return present_venue(venue, [])

    def add_location(self, venue_id: UUID, payload: LocationCreateIn) -> VenueOut:
        self.venues.get(venue_id)
        location = VenueLocation(id=new_id(), venue_id=venue_id, **payload.model_dump())
        self.venues.add_location(location)
        return present_venue(self.venues.get(venue_id), [])

    def list_deals(self) -> list[DealOut]:
        now = utcnow()
        result = []
        for deal in self.deals.list_all():
            result.append(
                present_deal(
                    deal,
                    now=now,
                    verification=self.deals.latest_verification(deal.id),
                    publication=deal.publications[0] if deal.publications else None,
                    flags=self.flags,
                )
            )
        return result

    def create_deal(self, payload: DealCreateIn, *, actor: str = "admin") -> DealOut:
        self.venues.get_location(payload.venue_location_id)
        deal = Deal(
            id=new_id(),
            venue_location_id=payload.venue_location_id,
            title=payload.title,
            description=payload.description,
            deal_type=payload.deal_type,
            offering_kind=payload.offering_kind,
            vertical=payload.vertical,
            status=payload.status,
            publication_state=payload.publication_state,
            source_confidence=payload.source_confidence,
        )
        self.deals.add(deal)
        for schedule in payload.schedules:
            self._add_schedule(deal.id, schedule)
        for item in payload.items:
            self._add_item(deal.id, item)
        source = self._manual_source_for_venue(payload.venue_location_id)
        publication = DealPublication(
            id=new_id(),
            deal_id=deal.id,
            source_id=source.id if source else None,
            published_by=actor,
            notes="Created in admin",
        )
        self.deals.add_publication(publication)
        self.verifications.add(
            Verification(
                id=new_id(),
                subject_type="deal",
                subject_id=deal.id,
                verification_type=VerificationType.MANUAL,
                verified_at=datetime.now(UTC),
                actor=actor,
                notes="Created in admin",
                confidence=Decimal("1.000"),
            )
        )
        self.db.flush()
        deal = self.deals.get(deal.id)
        return present_deal(
            deal,
            now=utcnow(),
            verification=self.deals.latest_verification(deal.id),
            publication=publication,
            source=source,
            flags=self.flags,
        )

    def update_deal(self, deal_id: UUID, payload: DealUpdateIn) -> DealOut:
        deal = self.deals.get(deal_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(deal, field, value)
        self.db.flush()
        return present_deal(
            deal,
            now=utcnow(),
            verification=self.deals.latest_verification(deal.id),
            flags=self.flags,
        )

    def add_schedule(self, deal_id: UUID, payload: ScheduleCreateIn) -> DealOut:
        self.deals.get(deal_id)
        self._add_schedule(deal_id, payload)
        return self.update_deal(deal_id, DealUpdateIn())

    def add_item(self, deal_id: UUID, payload: ItemCreateIn) -> DealOut:
        self.deals.get(deal_id)
        self._add_item(deal_id, payload)
        return self.update_deal(deal_id, DealUpdateIn())

    def verify_deal(self, deal_id: UUID, payload: VerifyIn) -> DealOut:
        deal = self.deals.get(deal_id)
        self.verifications.add(
            Verification(
                id=new_id(),
                subject_type="deal",
                subject_id=deal.id,
                verification_type=payload.verification_type,
                verified_at=datetime.now(UTC),
                actor=payload.actor,
                notes=payload.notes,
                confidence=Decimal("1.000"),
            )
        )
        return present_deal(
            self.deals.get(deal.id),
            now=utcnow(),
            verification=self.deals.latest_verification(deal.id),
            flags=self.flags,
        )

    def list_sources(self) -> list[SourceOut]:
        return [SourceOut.model_validate(source) for source in self.sources.list_all()]

    def create_source(self, payload: SourceCreateIn) -> SourceOut:
        identity = payload.canonical_identity or payload.url
        if self.sources.get_by_identity(identity):
            raise ConflictError("A source with this identity already exists")
        source = Source(
            id=new_id(),
            venue_id=payload.venue_id,
            source_type=payload.source_type,
            url=payload.url,
            canonical_identity=identity,
            is_active=True,
            crawl_enabled=payload.crawl_enabled,
            crawl_frequency_minutes=payload.crawl_frequency_minutes,
            trust_level=payload.trust_level,
        )
        self.sources.add(source)
        return SourceOut.model_validate(source)

    def disable_source(self, source_id: UUID) -> SourceOut:
        source = self.sources.get(source_id)
        source.is_active = False
        source.crawl_enabled = False
        self.db.flush()
        return SourceOut.model_validate(source)

    def list_snapshots(self, source_id: UUID, *, include_raw: bool = True) -> list[SnapshotOut]:
        self.sources.get(source_id)
        snapshots = self.sources.list_snapshots(source_id)
        return [
            SnapshotOut(
                id=snapshot.id,
                source_id=snapshot.source_id,
                crawl_run_id=snapshot.crawl_run_id,
                fetched_at=snapshot.fetched_at,
                http_status=snapshot.http_status,
                content_type=snapshot.content_type,
                content_hash=snapshot.content_hash,
                storage_ref=snapshot.storage_ref,
                parser_version=snapshot.parser_version,
                extra_metadata=snapshot.extra_metadata or {},
                raw_content=snapshot.raw_content if include_raw else None,
            )
            for snapshot in snapshots
        ]

    def list_candidates(self, review_status: str | None = None) -> list[CandidateOut]:
        return [
            CandidateOut.model_validate(candidate)
            for candidate in self.sources.list_candidates(review_status=review_status)
        ]

    def get_candidate(self, candidate_id: UUID) -> CandidateOut:
        return CandidateOut.model_validate(self.sources.get_candidate(candidate_id))

    def reject_candidate(self, candidate_id: UUID) -> CandidateOut:
        candidate = self.sources.get_candidate(candidate_id)
        candidate.review_status = "rejected"
        self.db.flush()
        return CandidateOut.model_validate(candidate)

    def list_runs(self, source_id: UUID | None = None) -> list[CrawlRunOut]:
        return [CrawlRunOut.model_validate(run) for run in self.sources.list_runs(source_id)]

    def _add_schedule(self, deal_id: UUID, payload: ScheduleCreateIn) -> None:
        if not payload.days_of_week:
            raise ValidationFailed("Schedule requires at least one weekday")
        self.deals.add_schedule(
            DealSchedule(
                id=new_id(),
                deal_id=deal_id,
                days_of_week=payload.days_of_week,
                start_time=payload.start_time,
                end_time=payload.end_time,
                ends_at_close=payload.ends_at_close,
                valid_from=payload.valid_from,
                valid_until=payload.valid_until,
            )
        )

    def _add_item(self, deal_id: UUID, payload: ItemCreateIn) -> None:
        self.deals.add_item(
            DealItem(
                id=new_id(),
                deal_id=deal_id,
                name=payload.name,
                description=payload.description,
                category=payload.category,
                normal_price=parse_money(payload.normal_price) if payload.normal_price is not None else None,
                deal_price=parse_money(payload.deal_price) if payload.deal_price is not None else None,
                currency=payload.currency,
            )
        )

    def _manual_source_for_venue(self, location_id: UUID) -> Source | None:
        location = self.venues.get_location(location_id)
        identity = f"manual:venue:{location.venue_id}"
        existing = self.sources.get_by_identity(identity)
        if existing:
            return existing
        source = Source(
            id=new_id(),
            venue_id=location.venue_id,
            source_type=SourceType.MANUAL,
            url=f"manual://venue/{location.venue_id}",
            canonical_identity=identity,
            is_active=True,
            crawl_enabled=False,
            trust_level="internal",
        )
        return self.sources.add(source)


def _unique_slug(db: Session, base: str) -> str:
    from sqlalchemy import select

    slug = base
    suffix = 2
    while db.scalar(select(Venue.id).where(Venue.slug == slug)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug
