from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.models.enums import CrawlRunStatus

if TYPE_CHECKING:
    from app.db.models.source import Source


class CrawlRun(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "crawl_runs"

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=CrawlRunStatus.STARTED, index=True)
    fetch_result: Mapped[str | None] = mapped_column(String(40))
    parse_result: Mapped[str | None] = mapped_column(String(40))
    extracted_count: Mapped[int] = mapped_column(Integer, default=0)
    error_category: Mapped[str | None] = mapped_column(String(80))
    error_details: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    source: Mapped["Source"] = relationship(back_populates="crawl_runs")
