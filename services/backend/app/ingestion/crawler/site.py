"""Multi-page website crawl for one restaurant (or one starting URL).

Given a homepage, we fetch a small number of high-value internal pages
(menu, happy hour, specials), store immutable snapshots, extract offer
candidates, and update freshness. One broken page cannot kill the job.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.ids import new_id
from app.core.logging import crawl_run_id_ctx, get_logger, ingestion_run_id_ctx
from app.db.models import CrawlRun, ExtractionCandidate, IngestionRun, Source, SourceSnapshot
from app.db.models.enums import (
    CandidateReviewStatus,
    CandidateValidationStatus,
    CrawlRunStatus,
    IngestionRunStatus,
)
from app.db.repositories.source_repository import SourceRepository
from app.db.repositories.venue_repository import VenueRepository
from app.ingestion.crawler.discovery import discover_internal_links, prioritize_urls
from app.ingestion.crawler.domain_health import record_host_attempt
from app.ingestion.crawler.html import ParsedPage
from app.ingestion.crawler.sighting import apply_source_sightings
from app.ingestion.extractors.html import HtmlOfferExtractor
from app.ingestion.fetchers.http import HttpFetcher
from app.ingestion.normalizers.deal import DealNormalizer
from app.ingestion.parsers.html_parser import HtmlParser
from app.ingestion.safety import content_hash
from app.ingestion.validators.deal import DealValidator

logger = get_logger("site_crawler")


class SiteCrawler:
    def __init__(self, db: Session, settings: Settings, fetcher: HttpFetcher) -> None:
        self.db = db
        self.settings = settings
        self.fetcher = fetcher
        self.sources = SourceRepository(db)
        self.venues = VenueRepository(db)
        self.parser = HtmlParser()
        self.extractor = HtmlOfferExtractor()
        self.normalizer = DealNormalizer()
        self.validator = DealValidator()

    def crawl(
        self,
        *,
        start_url: str,
        run: IngestionRun,
        source: Source,
        venue_location_id: UUID | None = None,
    ) -> IngestionRun:
        ingestion_run_id_ctx.set(str(run.id))
        run.status = IngestionRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        self.db.flush()
        crawl = CrawlRun(
            id=new_id(),
            source_id=source.id,
            ingestion_run_id=run.id,
            started_at=datetime.now(UTC),
            status=CrawlRunStatus.STARTED,
            requested_by=run.requested_by,
        )
        self.sources.add_run(crawl)
        crawl_run_id_ctx.set(str(crawl.id))
        errors: list[dict] = list(run.errors or [])
        page_texts: list[str] = []
        fetch_succeeded = False
        try:
            homepage = self._fetch_page(start_url, run, crawl)
            discovered: list[str] = []
            if homepage and homepage.content and not homepage.skipped_reason:
                html = homepage.content.decode("utf-8", errors="replace")
                discovered = discover_internal_links(html, homepage.final_url or start_url)
            urls = prioritize_urls(
                start_url,
                discovered,
                max_pages=min(self.settings.crawler_max_pages_per_domain, self.settings.crawler_max_pages_per_run),
            )
            run.pages_discovered = len(urls)
            crawl.pages_discovered = len(urls)
            for url in urls:
                if run.cancel_requested:
                    run.status = IngestionRunStatus.CANCELLED
                    break
                try:
                    fetched = (
                        homepage
                        if url.rstrip("/") == start_url.rstrip("/") and homepage
                        else self._fetch_page(url, run, crawl)
                    )
                    if fetched is None:
                        continue
                    if fetched.skipped_reason == "robots_disallow":
                        run.robots_blocked += 1
                        crawl.robots_blocked += 1
                        run.pages_skipped += 1
                        logger.info("page_skipped_robots", url=url)
                        continue
                    text = self._ingest_page(
                        source=source,
                        run=run,
                        crawl=crawl,
                        fetched=fetched,
                        venue_location_id=venue_location_id,
                    )
                    if text:
                        page_texts.append(text)
                        fetch_succeeded = True
                except Exception as exc:
                    errors.append({"url": url, "category": exc.__class__.__name__, "message": str(exc)[:500]})
                    run.pages_skipped += 1
                    logger.exception("page_failed", url=url)
                    continue
            run.errors = errors
            crawl.error_details = None if not errors else errors[0].get("message")
            if run.cancel_requested:
                crawl.status = CrawlRunStatus.CANCELLED
            elif errors and (run.pages_fetched or run.offers_discovered):
                run.status = IngestionRunStatus.PARTIAL
                crawl.status = CrawlRunStatus.PARTIAL
            elif errors and not run.pages_fetched:
                run.status = IngestionRunStatus.FAILED
                crawl.status = CrawlRunStatus.FAILED
            else:
                run.status = IngestionRunStatus.COMPLETED
                crawl.status = CrawlRunStatus.SUCCEEDED
                source.last_success_at = datetime.now(UTC)
                source.last_error = None
                source.consecutive_failures = 0
            if not run.cancel_requested:
                apply_source_sightings(
                    self.db,
                    source_id=source.id,
                    page_text="\n".join(page_texts),
                    fetch_succeeded=fetch_succeeded,
                    settings=self.settings,
                )
        except Exception as exc:
            run.status = IngestionRunStatus.FAILED
            run.error_category = exc.__class__.__name__
            run.error_details = str(exc)[:2000]
            crawl.status = CrawlRunStatus.FAILED
            crawl.error_category = exc.__class__.__name__
            crawl.error_details = str(exc)[:2000]
            source.last_failure_at = datetime.now(UTC)
            source.last_error = str(exc)[:2000]
            source.consecutive_failures = (source.consecutive_failures or 0) + 1
            logger.exception("site_crawl_failed", url=start_url)
            apply_source_sightings(
                self.db,
                source_id=source.id,
                page_text="",
                fetch_succeeded=False,
                settings=self.settings,
            )
        run.finished_at = datetime.now(UTC)
        crawl.completed_at = run.finished_at
        self.db.flush()
        return run

    def _fetch_page(self, url: str, run: IngestionRun, crawl: CrawlRun):
        fetched = self.fetcher.fetch(
            url,
            user_agent=self.settings.crawler_user_agent,
            timeout_seconds=self.settings.crawler_request_timeout_seconds,
        )
        run.pages_fetched += 1
        crawl.pages_fetched += 1
        robots = "disallow" if fetched.skipped_reason == "robots_disallow" else None
        record_host_attempt(
            self.db,
            fetched.final_url or fetched.url or url,
            success=fetched.skipped_reason is None and 200 <= fetched.http_status < 400,
            http_status=fetched.http_status,
            robots_status=robots,
            error=fetched.skipped_reason,
            duration_ms=fetched.duration_ms or None,
        )
        return fetched

    def _ingest_page(
        self,
        *,
        source: Source,
        run: IngestionRun,
        crawl: CrawlRun,
        fetched,
        venue_location_id: UUID | None,
    ) -> str:
        raw = fetched.content.decode("utf-8", errors="replace")[: self.settings.crawler_max_response_bytes]
        digest = content_hash(fetched.content)
        page_url = fetched.final_url or fetched.url
        hashes = dict((source.config or {}).get("page_hashes") or {})
        unchanged = hashes.get(page_url) == digest
        snapshot = SourceSnapshot(
            id=new_id(),
            source_id=source.id,
            crawl_run_id=crawl.id,
            fetched_at=datetime.now(UTC),
            http_status=fetched.http_status,
            content_type=fetched.content_type,
            content_hash=digest,
            storage_ref=f"inline:{source.id}",
            raw_content=raw,
            parser_version=self.parser.version,
            extra_metadata={
                "url": fetched.final_url or fetched.url,
                "last_modified": (fetched.headers or {}).get("last-modified"),
                "unchanged": unchanged,
            },
        )
        self.sources.add_snapshot(snapshot)
        if unchanged:
            # Same bytes as last time: skip expensive re-extraction. The page
            # text is still used later to confirm published offers remain present.
            logger.info("page_unchanged", url=fetched.url, content_hash=digest)
            run.records_skipped += 1
            return raw
        parsed = self.parser.parse(fetched)
        extracted = self.extractor.extract(parsed)
        run.offers_discovered += len(extracted)
        page = parsed.data if isinstance(parsed.data, ParsedPage) else None
        created = 0
        for item in extracted:
            normalized = self.normalizer.normalize(item.payload)
            if venue_location_id:
                normalized["venue_location_id"] = str(venue_location_id)
            elif (normalized.get("venue") or {}).get("name"):
                location = self.venues.find_location_for_venue_name(normalized["venue"]["name"])
                if location:
                    normalized["venue_location_id"] = str(location.id)
                    venue_location_id = location.id
            errors = self.validator.validate({**normalized, "confidence": item.confidence})
            if "low_confidence" in errors or item.confidence < 0.45:
                status = CandidateValidationStatus.QUARANTINED
            elif errors:
                status = CandidateValidationStatus.REJECTED
            else:
                status = CandidateValidationStatus.VALID
            existing = self.sources.find_candidate_by_hash(source.id, digest, normalized.get("title") or "")
            if existing and existing.review_status == CandidateReviewStatus.PENDING:
                run.records_skipped += 1
                continue
            self.sources.add_candidate(
                ExtractionCandidate(
                    id=new_id(),
                    source_snapshot_id=snapshot.id,
                    crawl_run_id=crawl.id,
                    venue_location_id=venue_location_id,
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
            run.offers_created += 1
            if item.confidence < 0.45 or "missing_schedule" in errors:
                from app.services.review_flags import flag_review

                flag_review(
                    self.db,
                    subject_type="candidate",
                    reason="low_confidence" if item.confidence < 0.45 else "unparsed_schedule",
                    title=normalized.get("title") or "Untitled offer",
                    explanation=item.diagnostic_notes or "Extractor was not confident enough to publish.",
                    suggested_action="Review the source page and edit or reject the candidate.",
                    evidence={"url": fetched.url, "raw_text": (item.payload or {}).get("raw_text")},
                    subject_id=None,
                )
        crawl.extracted_count += created
        hashes[page_url] = digest
        config = dict(source.config or {})
        config["page_hashes"] = hashes
        source.config = config
        source.last_content_hash = digest
        if page:
            snapshot.extra_metadata = {
                **(snapshot.extra_metadata or {}),
                "title": page.title,
                "canonical_url": page.canonical_url,
                "heading_count": len(page.headings),
                "json_ld_count": len(page.json_ld),
            }
        return page.text if page else raw
