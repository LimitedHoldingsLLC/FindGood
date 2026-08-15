from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.ids import new_id
from app.core.logging import crawl_run_id_ctx, get_logger
from app.db.models import CrawlRun, ExtractionCandidate, SourceSnapshot
from app.db.models.enums import (
    CandidateReviewStatus,
    CandidateValidationStatus,
    CrawlRunStatus,
    SourceType,
)
from app.db.repositories.source_repository import SourceRepository
from app.db.repositories.venue_repository import VenueRepository
from app.ingestion.extractors.demo import DemoExtractor
from app.ingestion.fetchers.demo import DemoFetcher
from app.ingestion.fetchers.http import HttpFetcher
from app.ingestion.normalizers.deal import DealNormalizer
from app.ingestion.parsers.json_parser import JsonParser
from app.ingestion.safety import content_hash
from app.ingestion.validators.deal import DealValidator

logger = get_logger("ingestion")


class IngestionPipeline:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.sources = SourceRepository(db)
        self.venues = VenueRepository(db)
        self.demo_fetcher = DemoFetcher()
        self.http_fetcher = HttpFetcher(
            max_bytes=settings.crawler_max_response_bytes,
            timeout_seconds=settings.crawler_request_timeout_seconds,
            user_agent=settings.crawler_user_agent,
        )
        self.parser = JsonParser()
        self.extractor = DemoExtractor()
        self.normalizer = DealNormalizer()
        self.validator = DealValidator()

    def run(self, source_id: UUID, *, retry_count: int = 0) -> CrawlRun:
        source = self.sources.get(source_id)
        if not source.is_active or not source.crawl_enabled:
            raise RuntimeError("Source is disabled")
        run = CrawlRun(
            id=new_id(),
            source_id=source.id,
            started_at=datetime.now(UTC),
            status=CrawlRunStatus.STARTED,
            retry_count=retry_count,
        )
        self.sources.add_run(run)
        crawl_run_id_ctx.set(str(run.id))
        logger.info("crawl_started", source_id=str(source.id), url=source.url)
        try:
            fetched = self._fetch(source.url, source.source_type)
            run.fetch_result = "ok"
            snapshot = SourceSnapshot(
                id=new_id(),
                source_id=source.id,
                crawl_run_id=run.id,
                fetched_at=datetime.now(UTC),
                http_status=fetched.http_status,
                content_type=fetched.content_type,
                content_hash=content_hash(fetched.content),
                storage_ref=f"inline:{source.id}",
                raw_content=fetched.content.decode("utf-8", errors="replace")[
                    : self.settings.crawler_max_response_bytes
                ],
                parser_version=None,
                extra_metadata={"url": fetched.url},
            )
            self.sources.add_snapshot(snapshot)
            parsed = self.parser.parse(fetched)
            snapshot.parser_version = parsed.parser_version
            run.parse_result = "ok"
            extracted = self.extractor.extract(parsed)
            created = 0
            for item in extracted:
                normalized = self.normalizer.normalize(item.payload)
                location = None
                venue_name = (normalized.get("venue") or {}).get("name")
                if venue_name:
                    location = self.venues.find_location_for_venue_name(venue_name)
                if location:
                    normalized["venue_location_id"] = str(location.id)
                errors = self.validator.validate({**normalized, "confidence": item.confidence})
                if "low_confidence" in errors:
                    status = CandidateValidationStatus.QUARANTINED
                elif errors:
                    status = CandidateValidationStatus.REJECTED
                else:
                    status = CandidateValidationStatus.VALID
                existing = self.sources.find_candidate_by_hash(
                    source.id, snapshot.content_hash, normalized.get("title") or ""
                )
                if existing and existing.review_status == CandidateReviewStatus.PENDING:
                    logger.info(
                        "candidate_deduplicated",
                        source_id=str(source.id),
                        title=normalized.get("title"),
                    )
                    continue
                self.sources.add_candidate(
                    ExtractionCandidate(
                        id=new_id(),
                        source_snapshot_id=snapshot.id,
                        crawl_run_id=run.id,
                        venue_location_id=location.id if location else None,
                        candidate_type=item.candidate_type,
                        payload=item.payload,
                        normalized_payload=normalized,
                        validation_status=status,
                        validation_errors=errors,
                        review_status=CandidateReviewStatus.PENDING,
                        extractor_version=self.extractor.version,
                        confidence=Decimal(str(item.confidence)),
                        diagnostic_notes=item.diagnostic_notes,
                    )
                )
                created += 1
            run.extracted_count = created
            run.status = CrawlRunStatus.SUCCEEDED
            run.completed_at = datetime.now(UTC)
            source.last_success_at = run.completed_at
            source.last_error = None
            logger.info(
                "crawl_succeeded",
                source_id=str(source.id),
                extracted_count=created,
                snapshot_id=str(snapshot.id),
            )
            return run
        except Exception as exc:
            run.status = CrawlRunStatus.FAILED
            run.completed_at = datetime.now(UTC)
            run.error_category = exc.__class__.__name__
            run.error_details = str(exc)
            source.last_failure_at = run.completed_at
            source.last_error = str(exc)
            logger.exception(
                "crawl_failed",
                source_id=str(source.id),
                error_category=run.error_category,
                retry_count=retry_count,
            )
            raise

    def _fetch(self, url: str, source_type: str):
        user_agent = self.settings.crawler_user_agent
        timeout_seconds = self.settings.crawler_request_timeout_seconds
        if url.startswith("demo://") or source_type == SourceType.DEMO:
            return self.demo_fetcher.fetch(url, user_agent=user_agent, timeout_seconds=timeout_seconds)
        return self.http_fetcher.fetch(url, user_agent=user_agent, timeout_seconds=timeout_seconds)
