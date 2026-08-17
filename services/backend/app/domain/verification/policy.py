"""Central freshness policy.

Every user-facing record should be able to answer: is this still trustworthy,
and when should we check again?

Do not scatter "if age > 7 days" through routes or jobs. Call this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

from app.db.models.enums import FreshnessStatus, SightingState

RecordKind = Literal[
    "venue_identity",
    "venue_contact",
    "hours",
    "happy_hour",
    "daily_special",
    "limited_time",
    "event",
    "generic_offer",
]


@dataclass(frozen=True)
class FreshnessWindows:
    """How quickly each kind of fact goes stale. Values come from settings."""

    business_stale_after_days: int = 30
    hours_stale_after_days: int = 14
    happy_hour_stale_after_days: int = 7
    special_stale_after_days: int = 3
    contact_stale_after_days: int = 21
    aging_ratio: float = 0.6


@dataclass(frozen=True)
class FreshnessDecision:
    status: FreshnessStatus
    next_refresh_at: datetime | None
    window_days: int
    reason: str


def window_days_for(kind: RecordKind, windows: FreshnessWindows) -> int:
    mapping: dict[RecordKind, int] = {
        "venue_identity": windows.business_stale_after_days,
        "venue_contact": windows.contact_stale_after_days,
        "hours": windows.hours_stale_after_days,
        "happy_hour": windows.happy_hour_stale_after_days,
        "daily_special": windows.special_stale_after_days,
        "limited_time": windows.special_stale_after_days,
        "event": windows.special_stale_after_days,
        "generic_offer": windows.happy_hour_stale_after_days,
    }
    return mapping[kind]


def deal_kind_from_type(deal_type: str | None) -> RecordKind:
    """Map a catalog deal_type onto a freshness window. Unknown types use the happy-hour window."""
    value = (deal_type or "").casefold()
    if value in {"happy_hour"}:
        return "happy_hour"
    if value in {"lunch", "limited_time", "percentage_off", "fixed_price", "bogo", "introductory"}:
        return "limited_time"
    if value in {"food_special", "drink_special", "taco_night", "oyster", "prix_fixe", "brunch", "late_night"}:
        return "daily_special"
    return "generic_offer"


def evaluate_freshness(
    *,
    kind: RecordKind,
    now: datetime,
    last_verified_at: datetime | None,
    last_seen_at: datetime | None = None,
    explicit_end_date: date | None = None,
    sighting_state: str | None = None,
    verification_failed: bool = False,
    windows: FreshnessWindows | None = None,
) -> FreshnessDecision:
    """Decide freshness_status and the next time a job should look at this record.

    Rules (conservative on purpose):
    - An explicit end date that has passed is expired, not merely stale.
    - A failed fetch is verification_failed, not "the offer disappeared".
    - last_seen_at is not used as verification by itself.
    - Never-verified records stay unverified until evidence exists.
    """
    policy = windows or FreshnessWindows()
    days = window_days_for(kind, policy)
    if explicit_end_date is not None and now.date() > explicit_end_date:
        return FreshnessDecision(
            status=FreshnessStatus.EXPIRED,
            next_refresh_at=None,
            window_days=days,
            reason="explicit_end_date_passed",
        )
    if sighting_state in {SightingState.EXPIRED, SightingState.REMOVED}:
        status = FreshnessStatus.EXPIRED if sighting_state == SightingState.EXPIRED else FreshnessStatus.STALE
        return FreshnessDecision(
            status=status,
            next_refresh_at=None,
            window_days=days,
            reason=f"sighting_{sighting_state}",
        )
    if verification_failed:
        retry_at = now + _backoff(1, days)
        return FreshnessDecision(
            status=FreshnessStatus.VERIFICATION_FAILED,
            next_refresh_at=retry_at,
            window_days=days,
            reason="verification_failed",
        )
    if last_verified_at is None:
        return FreshnessDecision(
            status=FreshnessStatus.UNVERIFIED,
            next_refresh_at=now,
            window_days=days,
            reason="never_verified",
        )
    verified = last_verified_at if last_verified_at.tzinfo else last_verified_at.replace(tzinfo=now.tzinfo)
    current = now if now.tzinfo else now.replace(tzinfo=verified.tzinfo)
    age = current - verified
    window = timedelta(days=days)
    aging_after = timedelta(days=max(days * policy.aging_ratio, 0.5))
    if age <= aging_after:
        status = FreshnessStatus.FRESH
        reason = "within_fresh_window"
    elif age <= window:
        status = FreshnessStatus.AGING
        reason = "approaching_stale_window"
    else:
        status = FreshnessStatus.STALE
        reason = "past_stale_window"
    remaining = window - age
    next_at = current + remaining if remaining.total_seconds() > 0 else current
    return FreshnessDecision(status=status, next_refresh_at=next_at, window_days=days, reason=reason)


def next_refresh_after_success(*, kind: RecordKind, now: datetime, windows: FreshnessWindows | None = None) -> datetime:
    policy = windows or FreshnessWindows()
    days = window_days_for(kind, policy)
    # Recheck a bit before the record would be labeled stale.
    return now + timedelta(days=max(days * policy.aging_ratio, 0.5))


def next_refresh_after_failure(*, failure_count: int, now: datetime) -> datetime:
    """Slow down on websites that keep failing so we do not hammer a dead host."""
    return now + _backoff(failure_count, base_days=1)


def _backoff(failure_count: int, base_days: float) -> timedelta:
    steps = max(failure_count, 1)
    hours = min(2 ** (steps - 1), 72)
    if base_days >= 1 and steps == 1:
        hours = max(hours, 4)
    return timedelta(hours=hours)


def consumer_may_show(*, freshness_status: str | None, publication_state: str, sighting_state: str | None) -> bool:
    """Consumer lists hide expired, removed, and clearly invalid offers.

    Stale offers are also hidden by default. Unverified seed/manual deals still
    appear so existing catalog rows are not silently dropped.
    """
    if publication_state != "published":
        return False
    if sighting_state in {SightingState.EXPIRED, SightingState.REMOVED}:
        return False
    if freshness_status in {
        FreshnessStatus.EXPIRED,
        FreshnessStatus.STALE,
        FreshnessStatus.VERIFICATION_FAILED,
    }:
        return False
    return True


def windows_from_settings(settings: object) -> FreshnessWindows:
    return FreshnessWindows(
        business_stale_after_days=int(getattr(settings, "business_stale_after_days", 30)),
        hours_stale_after_days=int(getattr(settings, "hours_stale_after_days", 14)),
        happy_hour_stale_after_days=int(getattr(settings, "happy_hour_stale_after_days", 7)),
        special_stale_after_days=int(getattr(settings, "special_stale_after_days", 3)),
        contact_stale_after_days=int(getattr(settings, "contact_stale_after_days", 21)),
        aging_ratio=float(getattr(settings, "aging_ratio", 0.6)),
    )
