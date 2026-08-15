from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VerificationFreshness:
    verified_at: datetime | None
    days_ago: int | None
    label: str
    is_fresh: bool


def describe_freshness(verified_at: datetime | None, now: datetime) -> VerificationFreshness:
    if verified_at is None:
        return VerificationFreshness(verified_at=None, days_ago=None, label="Not yet verified", is_fresh=False)
    verified = verified_at if verified_at.tzinfo else verified_at.replace(tzinfo=now.tzinfo)
    current = now if now.tzinfo else now.replace(tzinfo=verified.tzinfo)
    delta = current - verified
    days = max(delta.days, 0)
    if delta.total_seconds() < 24 * 3600 and days == 0:
        label = "Verified today"
        fresh = True
    elif days == 1:
        label = "Last verified 1 day ago"
        fresh = True
    else:
        label = f"Last verified {days} days ago"
        fresh = days <= 7
    return VerificationFreshness(verified_at=verified, days_ago=days, label=label, is_fresh=fresh)
