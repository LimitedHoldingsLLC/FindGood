"""Per-domain crawler health.

If restaurant.com has been timing out all week, we should slow down or stop
hammering it instead of retrying every venue on that domain independently.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class CrawlDomain(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "crawl_domains"

    host: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_http_status: Mapped[int | None] = mapped_column(Integer)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    robots_status: Mapped[str | None] = mapped_column(String(40))
    avg_response_ms: Mapped[float | None] = mapped_column(Numeric(10, 2))
    next_permitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(Text)
