from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
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
    cuisines: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    price_level: Mapped[int | None] = mapped_column(Integer, index=True)
    drink_kinds: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    accepts_reservations: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    features: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), index=True)
    rating_review_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_source_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_providers: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
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
    location_confidence: Mapped[str] = mapped_column(String(32), default="high_confidence", index=True)
    geocode_source: Mapped[str | None] = mapped_column(String(40))
    geocode_accuracy: Mapped[str | None] = mapped_column(String(40))
    coordinates_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    address_hash: Mapped[str | None] = mapped_column(String(64))
    map_demand_count: Mapped[int] = mapped_column(Integer, default=0)

    venue: Mapped[Venue] = relationship(back_populates="locations")
    deals: Mapped[list["Deal"]] = relationship(back_populates="venue_location")
