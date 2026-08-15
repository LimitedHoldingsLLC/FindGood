from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import CrawlRun, ExtractionCandidate, Source, SourceSnapshot


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, source_id: UUID) -> Source:
        source = self.db.get(Source, source_id)
        if source is None:
            raise NotFoundError("Source not found")
        return source

    def get_by_identity(self, canonical_identity: str) -> Source | None:
        return self.db.scalar(select(Source).where(Source.canonical_identity == canonical_identity))

    def list_all(self) -> list[Source]:
        return list(self.db.scalars(select(Source).order_by(Source.created_at.desc())))

    def add(self, source: Source) -> Source:
        self.db.add(source)
        self.db.flush()
        return source

    def stale_sources(self, *, now: datetime | None = None) -> list[Source]:
        current = now or datetime.now(UTC)
        sources = list(
            self.db.scalars(select(Source).where(Source.is_active.is_(True), Source.crawl_enabled.is_(True)))
        )
        due: list[Source] = []
        for source in sources:
            if source.last_success_at is None:
                due.append(source)
                continue
            age = current - source.last_success_at
            if age >= timedelta(minutes=source.crawl_frequency_minutes):
                due.append(source)
        return due

    def add_snapshot(self, snapshot: SourceSnapshot) -> SourceSnapshot:
        self.db.add(snapshot)
        self.db.flush()
        return snapshot

    def get_snapshot(self, snapshot_id: UUID) -> SourceSnapshot:
        snapshot = self.db.get(SourceSnapshot, snapshot_id)
        if snapshot is None:
            raise NotFoundError("Source snapshot not found")
        return snapshot

    def list_snapshots(self, source_id: UUID) -> list[SourceSnapshot]:
        stmt = (
            select(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id)
            .order_by(SourceSnapshot.fetched_at.desc())
        )
        return list(self.db.scalars(stmt))

    def add_run(self, run: CrawlRun) -> CrawlRun:
        self.db.add(run)
        self.db.flush()
        return run

    def get_run(self, run_id: UUID) -> CrawlRun:
        run = self.db.get(CrawlRun, run_id)
        if run is None:
            raise NotFoundError("Crawl run not found")
        return run

    def list_runs(self, source_id: UUID | None = None) -> list[CrawlRun]:
        stmt = select(CrawlRun).order_by(CrawlRun.started_at.desc())
        if source_id:
            stmt = stmt.where(CrawlRun.source_id == source_id)
        return list(self.db.scalars(stmt.limit(100)))

    def add_candidate(self, candidate: ExtractionCandidate) -> ExtractionCandidate:
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def get_candidate(self, candidate_id: UUID) -> ExtractionCandidate:
        stmt = (
            select(ExtractionCandidate)
            .options(selectinload(ExtractionCandidate.snapshot))
            .where(ExtractionCandidate.id == candidate_id)
        )
        candidate = self.db.scalar(stmt)
        if candidate is None:
            raise NotFoundError("Candidate not found")
        return candidate

    def list_candidates(self, *, review_status: str | None = None) -> list[ExtractionCandidate]:
        stmt = select(ExtractionCandidate).options(selectinload(ExtractionCandidate.snapshot))
        if review_status:
            stmt = stmt.where(ExtractionCandidate.review_status == review_status)
        return list(self.db.scalars(stmt.order_by(ExtractionCandidate.created_at.desc())))

    def find_candidate_by_hash(self, source_id: UUID, content_hash: str, title: str) -> ExtractionCandidate | None:
        stmt = (
            select(ExtractionCandidate)
            .join(SourceSnapshot)
            .where(SourceSnapshot.source_id == source_id, SourceSnapshot.content_hash == content_hash)
        )
        for candidate in self.db.scalars(stmt):
            payload = candidate.normalized_payload or candidate.payload or {}
            if payload.get("title") == title:
                return candidate
        return None
