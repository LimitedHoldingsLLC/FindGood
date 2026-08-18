"""Wire providers, crawler, and persistence into one ingestion entrypoint.

HTTP routes and workers call this module. They do not talk to Google, Yelp,
or restaurant websites themselves.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.core.exceptions import CrawlerBlockedByRobots, ProviderNotConfigured, ValidationFailed
from app.core.ids import new_id
from app.core.logging import get_logger, ingestion_run_id_ctx
from app.db.models import IngestionRun, Source, Venue
from app.db.models.enums import IngestionJobType, IngestionRunStatus, ProviderName, SourceType, TrustLevel
from app.db.models.error_event import ErrorEvent
from app.ingestion.crawler.rate_limit import CrawlRateLimiter
from app.ingestion.crawler.robots import RobotsChecker
from app.ingestion.crawler.site import SiteCrawler
from app.ingestion.fetchers.http import HttpFetcher
from app.ingestion.http import OutboundHttpClient
from app.ingestion.persist import BusinessPersister
from app.ingestion.providers.base import ProviderSearchQuery
from app.ingestion.providers.google_places import GooglePlacesAdapter
from app.ingestion.providers.opentable import OpenTableAdapter
from app.ingestion.providers.tripadvisor import TripadvisorAdapter
from app.ingestion.providers.yelp import YelpAdapter
from app.ingestion.safety import assert_public_http_url
from app.services.review_flags import flag_review

logger = get_logger("orchestrator")


class IngestionOrchestrator:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        *,
        http_client: OutboundHttpClient | None = None,
        redis_client: object | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.http = http_client or OutboundHttpClient(
            user_agent=settings.crawler_user_agent,
            timeout_seconds=settings.crawler_request_timeout_seconds,
            max_bytes=settings.crawler_max_response_bytes,
            max_redirects=settings.crawler_max_redirects,
            retry_count=settings.crawler_retry_count,
        )
        self.robots = RobotsChecker(
            self.http,
            user_agent=settings.crawler_user_agent,
            enabled=settings.crawler_respect_robots_txt,
        )
        self.rate_limiter = CrawlRateLimiter(
            global_concurrency=settings.crawler_max_concurrency,
            domain_concurrency=settings.crawler_domain_concurrency,
            per_domain_delay_seconds=settings.crawler_per_domain_delay_seconds,
            redis_client=redis_client,
        )
        self.fetcher = HttpFetcher(
            max_bytes=settings.crawler_max_response_bytes,
            timeout_seconds=settings.crawler_request_timeout_seconds,
            user_agent=settings.crawler_user_agent,
            client=self.http,
            robots=self.robots,
            rate_limiter=self.rate_limiter,
            respect_robots=settings.crawler_respect_robots_txt,
            allowed_content_types=settings.crawler_allowed_content_type_list,
        )
        self.google = GooglePlacesAdapter(
            api_key=settings.google_places_api_key,
            client=self.http,
            max_calls_per_run=settings.google_places_max_calls_per_run,
            enabled=settings.google_places_enabled,
        )
        self.yelp = YelpAdapter(
            api_key=settings.yelp_api_key,
            client=self.http,
            max_calls_per_run=settings.yelp_max_calls_per_run,
            enabled=settings.yelp_enabled,
        )
        self.tripadvisor = TripadvisorAdapter(
            api_key=settings.tripadvisor_api_key,
            client=self.http,
            max_calls_per_run=settings.tripadvisor_max_calls_per_run,
            enabled=settings.tripadvisor_enabled,
        )
        self.opentable = OpenTableAdapter(
            api_key=settings.opentable_api_key,
            enabled=settings.opentable_enabled,
        )
        self.persister = BusinessPersister(db, settings)

    def open_run(
        self,
        *,
        provider: str,
        job_type: str,
        requested_by: str,
        target_url: str | None = None,
        venue_id: UUID | None = None,
        source_id: UUID | None = None,
        extra: dict | None = None,
    ) -> IngestionRun:
        run = IngestionRun(
            id=new_id(),
            provider=provider,
            job_type=job_type,
            status=IngestionRunStatus.QUEUED,
            requested_by=requested_by,
            created_at=datetime.now(UTC),
            target_url=target_url,
            venue_id=venue_id,
            source_id=source_id,
            extra_metadata=extra or {},
        )
        self.db.add(run)
        self.db.flush()
        ingestion_run_id_ctx.set(str(run.id))
        return run

    def search_provider(
        self,
        provider: str,
        query: ProviderSearchQuery,
        *,
        requested_by: str,
        run: IngestionRun | None = None,
    ) -> IngestionRun:
        adapter = self._adapter(provider)
        run = run or self.open_run(
            provider=provider,
            job_type=IngestionJobType.PROVIDER_SEARCH,
            requested_by=requested_by,
            extra={"query": query.text, "city": query.city},
        )
        run.status = IngestionRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        errors: list[dict] = []
        try:
            businesses = adapter.search_businesses(query)
            run.records_discovered = len(businesses)
            for business in businesses:
                try:
                    result = self.persister.upsert(business)
                    if result.created:
                        run.records_created += 1
                    elif result.updated:
                        run.records_updated += 1
                    else:
                        run.records_skipped += 1
                    if result.needs_review and result.venue:
                        flag_review(
                            self.db,
                            subject_type="venue",
                            subject_id=result.venue.id,
                            reason="possible_duplicate_venue",
                            title=f"Possible duplicate: {business.name}",
                            explanation=(
                                "A newly imported restaurant looks similar to an existing one. "
                                f"Matching signals: {', '.join(result.match_reasons) or 'unclear'}."
                            ),
                            suggested_action="Merge if it is the same place, or ignore if it is not.",
                            evidence={"provider": provider, "provider_id": business.provider_business_id},
                        )
                except Exception as exc:
                    errors.append({"provider_id": business.provider_business_id, "message": str(exc)[:400]})
                    self._record_error(run, provider, "persist_failure", str(exc), None)
            run.errors = errors
            run.status = IngestionRunStatus.PARTIAL if errors else IngestionRunStatus.COMPLETED
            self._bump_usage(provider, calls=getattr(adapter, "calls_used", 0), imported=run.records_created)
        except ProviderNotConfigured:
            run.status = IngestionRunStatus.FAILED
            run.error_category = "ProviderNotConfigured"
            run.error_details = f"{provider} is not configured"
            raise
        except Exception as exc:
            run.status = IngestionRunStatus.FAILED
            run.error_category = exc.__class__.__name__
            run.error_details = str(exc)[:2000]
            self._record_error(run, provider, exc.__class__.__name__, str(exc), None)
            raise
        finally:
            run.finished_at = datetime.now(UTC)
            self.db.flush()
        return run

    def crawl_url(
        self,
        url: str,
        *,
        requested_by: str,
        venue_id: UUID | None = None,
        run: IngestionRun | None = None,
    ) -> IngestionRun:
        assert_public_http_url(url)
        source = self._source_for_url(url, venue_id)
        run = run or self.open_run(
            provider=ProviderName.WEBSITE_CRAWLER,
            job_type=IngestionJobType.WEBSITE_CRAWL,
            requested_by=requested_by,
            target_url=url,
            venue_id=venue_id,
            source_id=source.id,
        )
        if self.settings.crawler_respect_robots_txt and not self.robots.allowed(url):
            run.status = IngestionRunStatus.FAILED
            run.error_category = "robots_disallow"
            run.error_details = "robots.txt disallows this URL"
            run.robots_blocked = 1
            run.finished_at = datetime.now(UTC)
            self.db.flush()
            raise CrawlerBlockedByRobots("robots.txt disallows crawling this URL")
        location_id = None
        if venue_id:
            from sqlalchemy import select

            venue = self.db.scalar(select(Venue).options(selectinload(Venue.locations)).where(Venue.id == venue_id))
            if venue and venue.locations:
                location_id = venue.locations[0].id
        crawler = SiteCrawler(self.db, self.settings, self.fetcher)
        return crawler.crawl(start_url=url, run=run, source=source, venue_location_id=location_id)

    def refresh_provider_venue(self, provider: str, venue_id: UUID, *, requested_by: str) -> IngestionRun:
        from sqlalchemy import select

        from app.db.models.provider_link import VenueProviderLink

        link = self.db.scalar(
            select(VenueProviderLink).where(
                VenueProviderLink.venue_id == venue_id, VenueProviderLink.provider == provider
            )
        )
        run = self.open_run(
            provider=provider,
            job_type=IngestionJobType.PROVIDER_REFRESH,
            requested_by=requested_by,
            venue_id=venue_id,
        )
        if link is None:
            run.status = IngestionRunStatus.FAILED
            run.error_details = f"No {provider} link for this venue"
            run.finished_at = datetime.now(UTC)
            return run
        adapter = self._adapter(provider)
        run.status = IngestionRunStatus.RUNNING
        run.started_at = datetime.now(UTC)
        business = adapter.fetch_business(link.provider_business_id)
        if business:
            self.persister.upsert(business)
            run.records_updated = 1
            run.status = IngestionRunStatus.COMPLETED
        else:
            run.status = IngestionRunStatus.PARTIAL
            run.records_skipped = 1
        run.finished_at = datetime.now(UTC)
        self.db.flush()
        return run

    def _adapter(self, provider: str):
        mapping = {
            "google_places": self.google,
            "yelp": self.yelp,
            "tripadvisor": self.tripadvisor,
            "opentable": self.opentable,
        }
        adapter = mapping.get(provider)
        if adapter is None:
            raise ValidationFailed(f"Unknown provider: {provider}")
        return adapter

    def _source_for_url(self, url: str, venue_id: UUID | None) -> Source:
        identity = f"website:{url.rstrip('/')}"
        from sqlalchemy import select

        existing = self.db.scalar(select(Source).where(Source.canonical_identity == identity))
        if existing:
            if venue_id and existing.venue_id is None:
                existing.venue_id = venue_id
            return existing
        source = Source(
            id=new_id(),
            venue_id=venue_id,
            source_type=SourceType.RESTAURANT_WEBSITE,
            url=url,
            canonical_identity=identity,
            is_active=True,
            crawl_enabled=True,
            trust_level=TrustLevel.HIGH,
        )
        self.db.add(source)
        self.db.flush()
        return source

    def _record_error(self, run: IngestionRun, provider: str, category: str, message: str, url: str | None) -> None:
        self.db.add(
            ErrorEvent(
                id=new_id(),
                provider=provider,
                category=category,
                message=message[:2000],
                url=url,
                venue_id=run.venue_id,
                ingestion_run_id=run.id,
                created_at=datetime.now(UTC),
            )
        )

    def _bump_usage(self, provider: str, *, calls: int, imported: int) -> None:
        from datetime import date

        from sqlalchemy import select

        from app.db.models.provider_usage import ProviderUsageDaily

        day = date.today()
        row = self.db.scalar(
            select(ProviderUsageDaily).where(ProviderUsageDaily.provider == provider, ProviderUsageDaily.day == day)
        )
        if row is None:
            row = ProviderUsageDaily(id=new_id(), provider=provider, day=day)
            self.db.add(row)
        row.call_count += calls
        row.records_imported += imported
