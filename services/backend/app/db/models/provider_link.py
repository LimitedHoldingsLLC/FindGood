"""Maps a FindGood venue to a stable ID at an external provider.

A restaurant can appear in Google Places, Yelp, OpenTable, and its own website.
This table is how we remember "these four records are the same business" without
copying the restaurant into four separate venue rows.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.venue import Venue


class VenueProviderLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "venue_provider_links"
    __table_args__ = (UniqueConstraint("provider", "provider_business_id", name="uq_venue_provider_links_provider_id"),)

    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    provider_business_id: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_url: Mapped[str | None] = mapped_column(String(1000))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    venue: Mapped["Venue"] = relationship(back_populates="provider_links")
