"""Update published deals after a website crawl using last-seen rules.

We only look at deals that were published from this source. Offers on a
different page of the same site are checked against combined crawl text so a
homepage fetch does not mark a happy-hour-page deal as missing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Deal, DealPublication
from app.db.models.enums import FreshnessStatus, PublicationState, SightingState
from app.domain.verification.policy import (
    deal_kind_from_type,
    evaluate_freshness,
    next_refresh_after_failure,
    next_refresh_after_success,
    windows_from_settings,
)
from app.domain.verification.sighting import next_sighting_after_miss, offer_appears_on_page
from app.services.review_flags import flag_review

logger = get_logger("sighting")


def apply_source_sightings(
    db: Session,
    *,
    source_id: UUID,
    page_text: str,
    fetch_succeeded: bool,
    settings: object,
) -> None:
    now = datetime.now(UTC)
    windows = windows_from_settings(settings)
    deals = list(
        db.scalars(
            select(Deal)
            .join(DealPublication, DealPublication.deal_id == Deal.id)
            .where(
                DealPublication.source_id == source_id,
                Deal.publication_state == PublicationState.PUBLISHED,
                Deal.sighting_state.notin_([SightingState.EXPIRED, SightingState.REMOVED]),
            )
        )
    )
    if not deals:
        return
    if not fetch_succeeded:
        for deal in deals:
            deal.failure_count = (deal.failure_count or 0) + 1
            decision = evaluate_freshness(
                kind=deal_kind_from_type(deal.deal_type),
                now=now,
                last_verified_at=deal.last_verified_at,
                last_seen_at=deal.last_seen_at,
                sighting_state=deal.sighting_state,
                verification_failed=True,
                windows=windows,
            )
            deal.freshness_status = decision.status
            deal.next_refresh_at = next_refresh_after_failure(failure_count=deal.failure_count, now=now)
        logger.info("sighting_verification_failed", source_id=str(source_id), deals=len(deals))
        return

    for deal in deals:
        present = offer_appears_on_page(
            title=deal.title,
            raw_source_text=deal.raw_source_text,
            page_text=page_text,
        )
        if present:
            deal.last_seen_at = now
            deal.last_verified_at = now
            deal.consecutive_misses = 0
            deal.failure_count = 0
            deal.sighting_state = SightingState.ACTIVE
            deal.freshness_status = FreshnessStatus.FRESH
            deal.next_refresh_at = next_refresh_after_success(
                kind=deal_kind_from_type(deal.deal_type),
                now=now,
                windows=windows,
            )
            continue
        deal.consecutive_misses = (deal.consecutive_misses or 0) + 1
        deal.sighting_state = next_sighting_after_miss(deal.consecutive_misses)
        decision = evaluate_freshness(
            kind=deal_kind_from_type(deal.deal_type),
            now=now,
            last_verified_at=deal.last_verified_at,
            last_seen_at=deal.last_seen_at,
            sighting_state=deal.sighting_state,
            windows=windows,
        )
        deal.freshness_status = decision.status
        deal.next_refresh_at = decision.next_refresh_at or now
        if deal.sighting_state == SightingState.VERIFICATION_NEEDED:
            flag_review(
                db,
                subject_type="deal",
                reason="source_disappeared",
                title=deal.title,
                explanation="This offer was not found on a later crawl of its source page.",
                suggested_action="Re-check the restaurant website, then verify or mark expired.",
                evidence={"source_id": str(source_id), "consecutive_misses": deal.consecutive_misses},
                subject_id=deal.id,
            )
        logger.info(
            "offer_missed_on_source",
            deal_id=str(deal.id),
            misses=deal.consecutive_misses,
            sighting_state=deal.sighting_state,
        )
