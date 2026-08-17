"""One operator-facing ingestion job.

CrawlRun stays as the per-source fetch/parse attempt. IngestionRun is the
broader job an admin sees: "search Google in Silver Lake", "crawl this URL",
"refresh stale happy hours". One ingestion run can create several crawl runs.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.models.enums import IngestionJobType, IngestionRunStatus


class IngestionRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ingestion_runs"

    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(40), default=IngestionJobType.WEBSITE_CRAWL, index=True)
    status: Mapped[str] = mapped_column(String(20), default=IngestionRunStatus.QUEUED, index=True)
    requested_by: Mapped[str] = mapped_column(String(120), default="system")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_url: Mapped[str | None] = mapped_column(String(1000))
    venue_id: Mapped[UUID | None] = mapped_column(ForeignKey("venues.id"), index=True)
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("sources.id"), index=True)
    records_discovered: Mapped[int] = mapped_column(Integer, default=0)
    records_created: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    pages_discovered: Mapped[int] = mapped_column(Integer, default=0)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0)
    pages_skipped: Mapped[int] = mapped_column(Integer, default=0)
    robots_blocked: Mapped[int] = mapped_column(Integer, default=0)
    offers_discovered: Mapped[int] = mapped_column(Integer, default=0)
    offers_created: Mapped[int] = mapped_column(Integer, default=0)
    offers_updated: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_category: Mapped[str | None] = mapped_column(String(80))
    error_details: Mapped[str | None] = mapped_column(Text)
    errors: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
