"""Create review-queue rows without duplicating pending items for the same subject."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ids import new_id
from app.db.models import ReviewItem
from app.db.models.enums import ReviewItemStatus


def flag_review(
    db: Session,
    *,
    subject_type: str,
    reason: str,
    title: str,
    explanation: str,
    suggested_action: str | None = None,
    evidence: dict | None = None,
    subject_id: UUID | None = None,
) -> ReviewItem:
    stmt = select(ReviewItem).where(
        ReviewItem.subject_type == subject_type,
        ReviewItem.reason == reason,
        ReviewItem.status == ReviewItemStatus.PENDING,
    )
    if subject_id:
        stmt = stmt.where(ReviewItem.subject_id == subject_id)
    else:
        stmt = stmt.where(ReviewItem.title == title)
    existing = db.scalar(stmt.limit(1))
    if existing:
        return existing
    item = ReviewItem(
        id=new_id(),
        subject_type=subject_type,
        subject_id=subject_id,
        reason=reason,
        title=title[:300],
        explanation=explanation,
        suggested_action=suggested_action,
        evidence=evidence or {},
        created_at=datetime.now(UTC),
    )
    db.add(item)
    db.flush()
    return item
