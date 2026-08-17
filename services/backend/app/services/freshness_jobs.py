"""Background freshness maintenance. Jobs only select due rows via next_refresh_at."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.models.enums import FreshnessStatus, SightingState
from app.db.repositories.ops_repository import OpsRepository
from app.domain.verification.policy import deal_kind_from_type, evaluate_freshness, windows_from_settings

logger = get_logger("freshness_jobs")


def detect_and_mark_stale(db: Session, settings: Settings, *, limit: int = 200) -> int:
    now = datetime.now(UTC)
    windows = windows_from_settings(settings)
    ops = OpsRepository(db)
    updated = 0
    for deal in ops.due_deals(now, limit):
        end_dates = [s.valid_until for s in deal.schedules if s.valid_until]
        explicit_end = max(end_dates) if end_dates else None
        decision = evaluate_freshness(
            kind=deal_kind_from_type(deal.deal_type),
            now=now,
            last_verified_at=deal.last_verified_at,
            last_seen_at=deal.last_seen_at,
            explicit_end_date=explicit_end,
            sighting_state=deal.sighting_state,
            windows=windows,
        )
        deal.freshness_status = decision.status
        deal.next_refresh_at = decision.next_refresh_at
        if decision.status == FreshnessStatus.EXPIRED:
            deal.sighting_state = SightingState.EXPIRED
        updated += 1
    for venue in ops.due_venues(now, limit):
        decision = evaluate_freshness(
            kind="venue_identity",
            now=now,
            last_verified_at=venue.last_verified_at,
            last_seen_at=venue.last_seen_at,
            windows=windows,
        )
        venue.freshness_status = decision.status
        venue.next_refresh_at = decision.next_refresh_at
        updated += 1
    db.flush()
    logger.info("stale_records_updated", count=updated)
    return updated


def expire_finished_promotions(db: Session, settings: Settings, *, limit: int = 200) -> int:
    now = datetime.now(UTC)
    ops = OpsRepository(db)
    expired = 0
    for deal in ops.deals_with_ended_schedules(now.date(), limit):
        still_valid = [s for s in deal.schedules if s.valid_until is None or s.valid_until >= now.date()]
        if still_valid:
            continue
        deal.freshness_status = FreshnessStatus.EXPIRED
        deal.sighting_state = SightingState.EXPIRED
        deal.next_refresh_at = None
        expired += 1
    db.flush()
    logger.info("promotions_expired", count=expired)
    return expired
