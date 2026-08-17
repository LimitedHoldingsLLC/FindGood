"""Human review queue for ambiguous or risky ingestion outcomes.

Extraction candidates already hold unpublished deal drafts. This table is for
everything else an operator should look at: possible duplicates, disappeared
source text, repeated crawl failures, conflicting addresses, and similar.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.models.enums import ReviewItemStatus, ReviewReason


class ReviewItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "review_items"

    subject_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    subject_id: Mapped[UUID | None] = mapped_column(index=True)
    reason: Mapped[str] = mapped_column(String(60), default=ReviewReason.MANUAL, index=True)
    status: Mapped[str] = mapped_column(String(20), default=ReviewItemStatus.PENDING, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(120))
