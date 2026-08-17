from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import FreshnessStatus, RecordStatus, Vertical

if TYPE_CHECKING:
    from app.db.models.deal import Deal
    from app.db.models.provider_link import VenueProviderLink


class Venue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "venues"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    website_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(40))
    primary_category: Mapped[str] = mapped_column(String(80), default="restaurant", index=True)
    vertical: Mapped[str] = mapped_column(String(32), default=Vertical.FOOD, index=True)
    status: Mapped[str] = mapped_column(String(32), default=RecordStatus.PUBLISHED, index=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    freshness_status: Mapped[str] = mapped_column(String(32), default=FreshnessStatus.UNVERIFIED, index=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    locations: Mapped[list["VenueLocation"]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    provider_links: Mapped[list["VenueProviderLink"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan"
    )


class VenueLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "venue_locations"

    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(120), default="Main")
    address_line1: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="US")
    neighborhood: Mapped[str | None] = mapped_column(String(120), index=True)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Los_Angeles")
    status: Mapped[str] = mapped_column(String(32), default=RecordStatus.PUBLISHED, index=True)

    venue: Mapped[Venue] = relationship(back_populates="locations")
    deals: Mapped[list["Deal"]] = relationship(back_populates="venue_location")
