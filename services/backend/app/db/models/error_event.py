"""Individual ingestion errors, stored so the admin Error Center can group them.

We keep the message and category, not stack traces, so operators can see
"Yelp rate limit, 12 times today" without opening a terminal.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ErrorEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "error_events"

    provider: Mapped[str | None] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000))
    venue_id: Mapped[UUID | None] = mapped_column(ForeignKey("venues.id"), index=True)
    ingestion_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
