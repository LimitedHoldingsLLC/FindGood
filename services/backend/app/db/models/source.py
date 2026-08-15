from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import (
    CandidateReviewStatus,
    CandidateType,
    CandidateValidationStatus,
    SourceType,
    TrustLevel,
)

if TYPE_CHECKING:
    from app.db.models.crawl_run import CrawlRun


class Source(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sources"

    venue_id: Mapped[UUID | None] = mapped_column(ForeignKey("venues.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), default=SourceType.MANUAL, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    canonical_identity: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    crawl_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    crawl_frequency_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    trust_level: Mapped[str] = mapped_column(String(20), default=TrustLevel.MEDIUM)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=6)
    respect_robots_txt: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    snapshots: Mapped[list["SourceSnapshot"]] = relationship(back_populates="source")
    crawl_runs: Mapped[list["CrawlRun"]] = relationship(back_populates="source")


class SourceSnapshot(UUIDPrimaryKeyMixin, Base):
    """Immutable raw evidence. There is no updated_at on purpose."""

    __tablename__ = "source_snapshots"

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    crawl_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(200))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_ref: Mapped[str | None] = mapped_column(String(500))
    raw_content: Mapped[str | None] = mapped_column(Text)
    parser_version: Mapped[str | None] = mapped_column(String(40))
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    source: Mapped[Source] = relationship(back_populates="snapshots")


class ExtractionCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "extraction_candidates"

    source_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("source_snapshots.id"), nullable=False, index=True)
    crawl_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("crawl_runs.id"), index=True)
    venue_location_id: Mapped[UUID | None] = mapped_column(ForeignKey("venue_locations.id"))
    candidate_type: Mapped[str] = mapped_column(String(20), default=CandidateType.DEAL)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    normalized_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    validation_status: Mapped[str] = mapped_column(String(20), default=CandidateValidationStatus.PENDING, index=True)
    validation_errors: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    review_status: Mapped[str] = mapped_column(String(20), default=CandidateReviewStatus.PENDING, index=True)
    published_deal_id: Mapped[UUID | None] = mapped_column(ForeignKey("deals.id"))
    extractor_version: Mapped[str] = mapped_column(String(40), default="demo-1")
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.500"))
    diagnostic_notes: Mapped[str | None] = mapped_column(Text)

    snapshot: Mapped[SourceSnapshot] = relationship()
