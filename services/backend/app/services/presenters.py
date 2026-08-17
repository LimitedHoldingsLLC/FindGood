from datetime import UTC, datetime
from decimal import Decimal

from app.api.schemas import (
    AvailabilityOut,
    DealItemOut,
    DealOut,
    DealScheduleOut,
    DealScoreOut,
    LocationOut,
    ProvenanceOut,
    ScoreFactorOut,
    VenueCardOut,
    VenueOut,
    VerificationOut,
)
from app.core.feature_flags import FeatureFlags
from app.db.models import Deal, DealPublication, Source, Venue, VenueLocation
from app.db.models.verification import Verification
from app.domain.deals.money import savings
from app.domain.schedules.engine import (
    AvailabilityStatus,
    ScheduleWindow,
    evaluate_deal_availability,
)
from app.domain.scoring.service import DealScoringService, ScoreInput
from app.domain.verification.freshness import describe_freshness
from app.domain.verification.policy import deal_kind_from_type, evaluate_freshness

_scorer = DealScoringService()


def location_out(location: VenueLocation) -> LocationOut:
    return LocationOut.model_validate(location)


def venue_card(venue: Venue, location: VenueLocation) -> VenueCardOut:
    return VenueCardOut(
        id=venue.id,
        name=venue.name,
        slug=venue.slug,
        primary_category=venue.primary_category,
        vertical=venue.vertical,
        neighborhood=location.neighborhood,
        city=location.city,
        timezone=location.timezone,
    )


def present_deal(
    deal: Deal,
    *,
    now: datetime,
    verification: Verification | None,
    publication: DealPublication | None = None,
    source: Source | None = None,
    flags: FeatureFlags,
    origin: tuple[Decimal, Decimal] | None = None,
) -> DealOut:
    location = deal.venue_location
    venue = location.venue
    windows = [
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
    availability = evaluate_deal_availability(windows, location.timezone, now)
    freshness = describe_freshness(verification.verified_at if verification else None, now)
    last_verified = getattr(deal, "last_verified_at", None) or (verification.verified_at if verification else None)
    end_dates = [schedule.valid_until for schedule in deal.schedules if schedule.valid_until]
    explicit_end = max(end_dates) if end_dates else None
    policy = evaluate_freshness(
        kind=deal_kind_from_type(deal.deal_type),
        now=now,
        last_verified_at=last_verified,
        last_seen_at=getattr(deal, "last_seen_at", None),
        explicit_end_date=explicit_end,
        sighting_state=getattr(deal, "sighting_state", None),
    )
    items = []
    for item in deal.items:
        absolute, percent = savings(item.normal_price, item.deal_price)
        items.append(
            DealItemOut(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                normal_price=item.normal_price,
                deal_price=item.deal_price,
                currency=item.currency,
                absolute_savings=absolute,
                percent_savings=percent,
            )
        )
    score = None
    if flags.deal_score:
        result = _scorer.score(
            ScoreInput(
                normal_prices=[item.normal_price for item in deal.items],
                deal_prices=[item.deal_price for item in deal.items],
                item_count=len(deal.items),
                last_verified_at=verification.verified_at if verification else None,
                availability_status=availability.status,
                now=now,
            )
        )
        score = DealScoreOut(
            score=result.score,
            factors=[ScoreFactorOut.model_validate(factor) for factor in result.factors],
        )
    provenance = None
    if publication or source:
        provenance = ProvenanceOut(
            source_type=source.source_type if source else None,
            source_url=source.url if source else None,
            snapshot_id=publication.source_snapshot_id if publication else None,
            published_by=publication.published_by if publication else None,
            published_at=publication.created_at if publication else None,
        )
    distance = None
    if origin is not None:
        distance = _haversine_km(
            float(origin[0]), float(origin[1]), float(location.latitude), float(location.longitude)
        )
    return DealOut(
        id=deal.id,
        title=deal.title,
        description=deal.description,
        deal_type=deal.deal_type,
        offering_kind=deal.offering_kind,
        vertical=deal.vertical,
        source_confidence=deal.source_confidence,
        venue=venue_card(venue, location),
        location=location_out(location),
        items=items,
        schedules=[DealScheduleOut.model_validate(schedule) for schedule in deal.schedules],
        availability=AvailabilityOut(
            status=availability.status.value,
            timezone=availability.timezone,
            local_time=availability.local_time,
            ends_at=availability.ends_at,
            next_occurrence=availability.next_occurrence,
            label=availability.label,
        ),
        verification=VerificationOut(
            verification_type=verification.verification_type if verification else "none",
            verified_at=verification.verified_at if verification else None,
            actor=verification.actor if verification else None,
            label=freshness.label,
            days_ago=freshness.days_ago,
            is_fresh=freshness.is_fresh,
        ),
        provenance=provenance,
        score=score,
        distance_km=distance,
        freshness_status=policy.status.value,
        last_seen_at=getattr(deal, "last_seen_at", None),
        last_verified_at=last_verified,
    )


def present_venue(
    venue: Venue,
    deals: list[DealOut],
) -> VenueOut:
    current = [
        deal
        for deal in deals
        if deal.availability.status in {AvailabilityStatus.ACTIVE_NOW.value, AvailabilityStatus.STARTS_SOON.value}
    ]
    upcoming = [deal for deal in deals if deal not in current]
    return VenueOut(
        id=venue.id,
        name=venue.name,
        slug=venue.slug,
        description=venue.description,
        website_url=venue.website_url,
        phone=venue.phone,
        primary_category=venue.primary_category,
        vertical=venue.vertical,
        status=venue.status,
        locations=[location_out(location) for location in venue.locations],
        current_deals=current,
        upcoming_deals=upcoming,
    )


def utcnow() -> datetime:
    return datetime.now(UTC)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    origin = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return round(2 * 6371 * asin(sqrt(origin)), 2)
