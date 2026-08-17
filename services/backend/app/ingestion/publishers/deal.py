from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationFailed
from app.core.feature_flags import FeatureFlags
from app.core.ids import new_id
from app.core.logging import get_logger
from app.db.models import Deal, DealItem, DealPublication, DealSchedule
from app.db.models.enums import (
    CandidateReviewStatus,
    CandidateValidationStatus,
    PublicationState,
    RecordStatus,
    VerificationType,
)
from app.db.models.verification import Verification
from app.db.repositories.deal_repository import DealRepository
from app.db.repositories.source_repository import SourceRepository
from app.db.repositories.venue_repository import VenueRepository
from app.db.repositories.verification_repository import VerificationRepository
from app.domain.deals.money import parse_money

logger = get_logger("publisher")


class DealPublisher:
    def __init__(self, db: Session, flags: FeatureFlags) -> None:
        self.db = db
        self.flags = flags
        self.sources = SourceRepository(db)
        self.venues = VenueRepository(db)
        self.deals = DealRepository(db)
        self.verifications = VerificationRepository(db)

    def publish(self, candidate_id: UUID, *, actor: str) -> Deal:
        candidate = self.sources.get_candidate(candidate_id)
        if candidate.validation_status not in {
            CandidateValidationStatus.VALID,
            CandidateValidationStatus.PENDING,
        }:
            if candidate.validation_status == CandidateValidationStatus.REJECTED:
                raise ValidationFailed("Rejected candidates cannot be published")
        if candidate.review_status == CandidateReviewStatus.APPROVED and candidate.published_deal_id:
            return self.deals.get(candidate.published_deal_id)

        payload = candidate.normalized_payload or candidate.payload
        location_id = candidate.venue_location_id
        if location_id is None and payload.get("venue_location_id"):
            location_id = UUID(payload["venue_location_id"])
        if location_id is None:
            raise ValidationFailed("Candidate is missing a venue location")
        location = self.venues.get_location(location_id)
        venue = self.venues.get(location.venue_id)
        deal = Deal(
            id=new_id(),
            venue_location_id=location_id,
            title=payload.get("title") or "Untitled deal",
            description=payload.get("description"),
            deal_type=payload.get("deal_type") or "other",
            offering_kind=payload.get("offering_kind") or "both",
            vertical=payload.get("vertical") or venue.vertical,
            status=RecordStatus.PUBLISHED,
            publication_state=PublicationState.PUBLISHED,
            source_confidence=candidate.confidence,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
            last_verified_at=datetime.now(UTC),
            freshness_status="fresh",
            extraction_method=(candidate.normalized_payload or {}).get("extraction_method") or "deterministic",
            raw_source_text=(candidate.payload or {}).get("raw_text"),
        )
        self.deals.add(deal)
        for schedule in payload.get("schedules") or []:
            self.deals.add_schedule(
                DealSchedule(
                    id=new_id(),
                    deal_id=deal.id,
                    days_of_week=schedule.get("days_of_week") or [],
                    start_time=_parse_time(schedule.get("start_time")),
                    end_time=_parse_time(schedule.get("end_time")),
                    ends_at_close=bool(schedule.get("ends_at_close")),
                    valid_from=_parse_date(schedule.get("valid_from")),
                    valid_until=_parse_date(schedule.get("valid_until")),
                )
            )
        for item in payload.get("items") or []:
            self.deals.add_item(
                DealItem(
                    id=new_id(),
                    deal_id=deal.id,
                    name=item.get("name") or "Untitled item",
                    description=item.get("description"),
                    category=item.get("category"),
                    normal_price=_price(item.get("normal_price")),
                    deal_price=_price(item.get("deal_price")),
                    currency=item.get("currency") or "USD",
                )
            )
        snapshot = candidate.snapshot
        publication = DealPublication(
            id=new_id(),
            deal_id=deal.id,
            candidate_id=candidate.id,
            source_snapshot_id=snapshot.id if snapshot else candidate.source_snapshot_id,
            source_id=snapshot.source_id if snapshot else None,
            published_by=actor,
            notes="Published from extraction candidate",
        )
        self.deals.add_publication(publication)
        self.verifications.add(
            Verification(
                id=new_id(),
                subject_type="deal",
                subject_id=deal.id,
                verification_type=VerificationType.AUTOMATED_SOURCE,
                verified_at=datetime.now(UTC),
                actor=actor,
                notes="Published from approved candidate",
                confidence=candidate.confidence,
            )
        )
        candidate.review_status = CandidateReviewStatus.APPROVED
        candidate.published_deal_id = deal.id
        logger.info(
            "candidate_published",
            candidate_id=str(candidate.id),
            deal_id=str(deal.id),
            snapshot_id=str(candidate.source_snapshot_id),
            actor=actor,
        )
        self.db.flush()
        return self.deals.get(deal.id)


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M").time()


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _price(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    return parse_money(value)
