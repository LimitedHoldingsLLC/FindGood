"""Daily call counters for paid/limited provider APIs.

This is how we keep Google and Yelp usage visible in the admin dashboard
without logging secrets or inventing dollar amounts we do not actually know.
"""

from datetime import date

from sqlalchemy import Date, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ProviderUsageDaily(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "provider_usage_daily"
    __table_args__ = (UniqueConstraint("provider", "day", name="uq_provider_usage_daily_provider_day"),)

    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit_count: Mapped[int] = mapped_column(Integer, default=0)
    records_imported: Mapped[int] = mapped_column(Integer, default=0)
