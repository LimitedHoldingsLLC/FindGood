from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.verification import Verification


class VerificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, verification: Verification) -> Verification:
        self.db.add(verification)
        self.db.flush()
        return verification

    def latest(self, subject_type: str, subject_id: UUID) -> Verification | None:
        stmt = (
            select(Verification)
            .where(Verification.subject_type == subject_type, Verification.subject_id == subject_id)
            .order_by(Verification.verified_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
