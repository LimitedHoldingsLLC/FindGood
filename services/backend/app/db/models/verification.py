from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.db.models.enums import VerificationType


class Verification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "verifications"

    subject_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    subject_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    verification_type: Mapped[str] = mapped_column(String(40), default=VerificationType.MANUAL, index=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=Decimal("1.000"))
