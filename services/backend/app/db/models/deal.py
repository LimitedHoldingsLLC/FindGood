from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DealOfferingKind, DealType, PublicationState, RecordStatus, Vertical

if TYPE_CHECKING:
    from app.db.models.source import ExtractionCandidate, SourceSnapshot
    from app.db.models.venue import VenueLocation


class Deal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deals"

    venue_location_id: Mapped[UUID] = mapped_column(ForeignKey("venue_locations.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    deal_type: Mapped[str] = mapped_column(String(40), default=DealType.OTHER, index=True)
    offering_kind: Mapped[str] = mapped_column(String(16), default=DealOfferingKind.BOTH, index=True)
    vertical: Mapped[str] = mapped_column(String(32), default=Vertical.FOOD, index=True)
    status: Mapped[str] = mapped_column(String(32), default=RecordStatus.PUBLISHED, index=True)
    publication_state: Mapped[str] = mapped_column(String(32), default=PublicationState.UNPUBLISHED, index=True)
    source_confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("0.500"))

    venue_location: Mapped[VenueLocation] = relationship(back_populates="deals")
    schedules: Mapped[list[DealSchedule]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    items: Mapped[list[DealItem]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    publications: Mapped[list[DealPublication]] = relationship(back_populates="deal")


class DealSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deal_schedules"

    deal_id: Mapped[UUID] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    days_of_week: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    ends_at_close: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)

    deal: Mapped[Deal] = relationship(back_populates="schedules")


class DealItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "deal_items"

    deal_id: Mapped[UUID] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(80))
    normal_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    deal_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    deal: Mapped[Deal] = relationship(back_populates="items")


class DealPublication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Provenance link: why a consumer-visible deal exists."""

    __tablename__ = "deal_publications"

    deal_id: Mapped[UUID] = mapped_column(ForeignKey("deals.id"), nullable=False, index=True)
    candidate_id: Mapped[UUID | None] = mapped_column(ForeignKey("extraction_candidates.id"), unique=True)
    source_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("source_snapshots.id"))
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("sources.id"))
    published_by: Mapped[str] = mapped_column(String(80), default="system")
    notes: Mapped[str | None] = mapped_column(Text)

    deal: Mapped[Deal] = relationship(back_populates="publications")
    candidate: Mapped[ExtractionCandidate | None] = relationship()
    source_snapshot: Mapped[SourceSnapshot | None] = relationship()
