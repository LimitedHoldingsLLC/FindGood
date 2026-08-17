"""Record per-host crawler health so we can stop hammering broken websites.

restaurant.com failing all week should slow down independently of other venues.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db.models import CrawlDomain
from app.domain.verification.policy import next_refresh_after_failure


def host_from_url(url: str) -> str | None:
    host = (urlparse(url).hostname or "").casefold().strip(".")
    return host or None


def record_host_attempt(
    db: Session,
    url: str,
    *,
    success: bool,
    http_status: int | None = None,
    robots_status: str | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
    failure_streak: int | None = None,
) -> CrawlDomain | None:
    host = host_from_url(url)
    if not host:
        return None
    row = db.scalar(select(CrawlDomain).where(CrawlDomain.host == host))
    if row is None:
        row = CrawlDomain(id=new_id(), host=host)
        db.add(row)
    now = datetime.now(UTC)
    row.last_attempt_at = now
    if http_status is not None:
        row.last_http_status = http_status
    if robots_status:
        row.robots_status = robots_status
    if duration_ms is not None:
        previous = float(row.avg_response_ms or duration_ms)
        row.avg_response_ms = round((previous + duration_ms) / 2, 2)
    if success:
        row.last_success_at = now
        row.success_count = (row.success_count or 0) + 1
        row.consecutive_failures = 0
        row.last_error = None
        row.next_permitted_at = None
    elif robots_status == "disallow":
        # robots.txt is a skip, not a dead host.
        row.last_error = error or "robots_disallow"
    else:
        row.last_failure_at = now
        row.failure_count = (row.failure_count or 0) + 1
        row.consecutive_failures = (row.consecutive_failures or 0) + 1
        row.last_error = (error or "fetch_failed")[:2000]
        streak = failure_streak if failure_streak is not None else row.consecutive_failures
        row.next_permitted_at = next_refresh_after_failure(failure_count=streak, now=now)
    db.flush()
    return row
