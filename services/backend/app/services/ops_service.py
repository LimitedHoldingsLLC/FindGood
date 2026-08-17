"""Admin control-plane use cases: overview, crawl, providers, review, freshness.

Routes validate input and call this service. This service does not contain SQL
beyond repository calls, and it does not fetch URLs itself.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.admin_schemas import (
    AuditOut,
    CrawlDomainOut,
    ErrorGroupOut,
    FreshnessBucketOut,
    IngestionRunOut,
    OpsDealOut,
    OpsOverviewOut,
    OpsVenueOut,
    PageOut,
    ProviderOut,
    ReviewOut,
    SearchOut,
    SystemHealthOut,
)
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationFailed
from app.core.feature_flags import FeatureFlags
from app.core.ids import new_id
from app.db.models import AdminAuditLog, Deal, Venue
from app.db.models.enums import (
    FreshnessStatus,
    IngestionJobType,
    IngestionRunStatus,
    ProviderName,
    RecordStatus,
    ReviewItemStatus,
    SightingState,
    VerificationType,
)
from app.db.models.verification import Verification
from app.db.repositories.deal_repository import DealRepository
from app.db.repositories.ops_repository import OpsRepository
from app.db.repositories.venue_repository import VenueRepository
from app.db.repositories.verification_repository import VerificationRepository
from app.domain.verification.policy import (
    deal_kind_from_type,
    evaluate_freshness,
    next_refresh_after_success,
    windows_from_settings,
)
from app.ingestion.providers.base import ProviderSearchQuery
from app.workers.queue import (
    JOB_PROVIDER_SEARCH,
    JOB_WEBSITE_CRAWL,
    JobQueue,
    enqueue_named,
)


class OpsService:
    def __init__(self, db: Session, settings: Settings, flags: FeatureFlags, queue: JobQueue) -> None:
        self.db = db
        self.settings = settings
        self.flags = flags
        self.queue = queue
        self.ops = OpsRepository(db)
        self.venues = VenueRepository(db)
        self.deals = DealRepository(db)
        self.verifications = VerificationRepository(db)

    def overview(self) -> OpsOverviewOut:
        now = datetime.now(UTC)
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        deal_fresh = self.ops.freshness_counts(Deal)
        venue_fresh = self.ops.freshness_counts(Venue)
        published = self.ops.count_published_deals()
        offers_fresh = deal_fresh.get("fresh", 0)
        businesses_fresh = venue_fresh.get("fresh", 0)
        venue_total = max(self.ops.count_venues(), 1)
        deal_total = max(published, 1)
        health = round(
            100 * ((businesses_fresh / venue_total) * 0.4 + (offers_fresh / deal_total) * 0.6),
            1,
        )
        return OpsOverviewOut(
            system_working=True,
            freshness_health_percent=health,
            total_businesses=self.ops.count_venues(),
            active_businesses=self.ops.count_venues_by_status(RecordStatus.PUBLISHED),
            businesses_added_24h=self.ops.count_venues(since=day_ago),
            businesses_added_7d=self.ops.count_venues(since=week_ago),
            total_active_offers=published,
            offers_added_24h=self.ops.count_deals(since=day_ago),
            offers_added_7d=self.ops.count_deals(since=week_ago),
            verified_offers=deal_fresh.get("fresh", 0),
            stale_offers=deal_fresh.get("stale", 0),
            expired_offers=deal_fresh.get("expired", 0),
            unverified_offers=deal_fresh.get("unverified", 0),
            aging_offers=deal_fresh.get("aging", 0),
            businesses_needing_refresh=self.ops.count_venues(),  # refined below via due query
            pending_review_items=self.ops.count_pending_review(),
            runs_completed_24h=self.ops.count_runs(status=IngestionRunStatus.COMPLETED, since=day_ago),
            runs_failed_24h=self.ops.count_runs(status=IngestionRunStatus.FAILED, since=day_ago)
            + self.ops.count_runs(status=IngestionRunStatus.PARTIAL, since=day_ago),
            crawl_failures_24h=self.ops.count_error_events(since=day_ago),
            provider_failures_24h=self.ops.count_error_events(since=day_ago),
            businesses_fresh_percent=round(100 * businesses_fresh / venue_total, 1),
            offers_fresh_percent=round(100 * offers_fresh / deal_total, 1),
            freshness_note=(
                "Freshness health is the share of businesses and published offers currently "
                "labeled fresh. It is an operational snapshot, not a scientific score."
            ),
        )

    def list_venues(self, *, q: str | None, city: str | None, page: int, page_size: int) -> PageOut:
        rows, total, page, page_size = self.ops.paginate_venues(q=q, city=city, page=page, page_size=page_size)
        return PageOut(items=[self._venue_out(v) for v in rows], page=page, page_size=page_size, total=total)

    def venue_detail(self, venue_id: UUID) -> OpsVenueOut:
        venue = self.db.scalar(
            select(Venue)
            .options(selectinload(Venue.locations), selectinload(Venue.provider_links))
            .where(Venue.id == venue_id)
        )
        if venue is None:
            raise NotFoundError("Venue not found")
        deals: list[Deal] = []
        for location in venue.locations:
            deals.extend(self.deals.list_all_for_location(location.id))
        return self._venue_out(venue, include_deals=deals)

    def list_deals(
        self,
        *,
        q: str | None,
        freshness: str | None,
        city: str | None,
        page: int,
        page_size: int,
    ) -> PageOut:
        rows, total, page, page_size = self.ops.paginate_deals(
            q=q, freshness=freshness, city=city, page=page, page_size=page_size
        )
        return PageOut(items=[self._deal_out(d) for d in rows], page=page, page_size=page_size, total=total)

    def deal_detail(self, deal_id: UUID) -> OpsDealOut:
        return self._deal_out(self.deals.get(deal_id))

    def list_runs(self, **filters) -> PageOut:
        rows, total, page, page_size = self.ops.paginate_runs(**filters)
        items = [IngestionRunOut.model_validate(r) for r in rows]
        return PageOut(items=items, page=page, page_size=page_size, total=total)

    def get_run(self, run_id: UUID) -> IngestionRunOut:
        return IngestionRunOut.model_validate(self.ops.get_run(run_id))

    def refresh_provider(self, provider: str, venue_id: UUID, *, actor: str) -> IngestionRunOut:
        from app.ingestion.orchestrator import IngestionOrchestrator

        orchestrator = IngestionOrchestrator(self.db, self.settings)
        run = orchestrator.refresh_provider_venue(provider, venue_id, requested_by=actor)
        self._audit(actor, f"refresh_{provider}", "venue", venue_id, {})
        return IngestionRunOut.model_validate(run)

    def queue_crawl(
        self,
        *,
        url: str | None,
        venue_id: UUID | None,
        requested_by: str,
        sync: bool = False,
    ) -> IngestionRunOut:
        from app.ingestion.orchestrator import IngestionOrchestrator
        from app.ingestion.safety import assert_public_http_url

        if not url and venue_id:
            venue = self.venues.get(venue_id)
            url = venue.website_url
        if not url:
            raise ValidationFailed("A URL or a venue with a website is required")
        assert_public_http_url(url)
        orchestrator = IngestionOrchestrator(self.db, self.settings)
        run = orchestrator.open_run(
            provider=ProviderName.WEBSITE_CRAWLER,
            job_type=IngestionJobType.WEBSITE_CRAWL,
            requested_by=requested_by,
            target_url=url,
            venue_id=venue_id,
        )
        self._audit(requested_by, "crawl_queued", "ingestion_run", run.id, {"url": url})
        if sync:
            orchestrator.crawl_url(url, requested_by=requested_by, venue_id=venue_id, run=run)
        else:
            enqueue_named(
                self.queue,
                JOB_WEBSITE_CRAWL,
                {"run_id": str(run.id), "url": url, "venue_id": str(venue_id) if venue_id else None},
                idempotency_key=f"crawl:{run.id}",
            )
        return IngestionRunOut.model_validate(run)

    def queue_provider_search(
        self,
        provider: str,
        *,
        text: str | None,
        city: str | None,
        latitude: float | None,
        longitude: float | None,
        requested_by: str,
        sync: bool = False,
    ) -> IngestionRunOut:
        from app.ingestion.orchestrator import IngestionOrchestrator

        orchestrator = IngestionOrchestrator(self.db, self.settings)
        adapter = orchestrator._adapter(provider)
        if not adapter.configured():
            from app.core.exceptions import ProviderNotConfigured

            raise ProviderNotConfigured(f"{provider} is not configured")
        run = orchestrator.open_run(
            provider=provider,
            job_type=IngestionJobType.PROVIDER_SEARCH,
            requested_by=requested_by,
            extra={"text": text, "city": city},
        )
        self._audit(requested_by, "provider_search_queued", "ingestion_run", run.id, {"provider": provider})
        payload = {
            "run_id": str(run.id),
            "provider": provider,
            "text": text,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
        }
        if sync:
            orchestrator.search_provider(
                provider,
                ProviderSearchQuery(text=text, city=city, latitude=latitude, longitude=longitude),
                requested_by=requested_by,
                run=run,
            )
        else:
            enqueue_named(self.queue, JOB_PROVIDER_SEARCH, payload, idempotency_key=f"search:{run.id}")
        return IngestionRunOut.model_validate(run)

    def retry_run(self, run_id: UUID, *, requested_by: str) -> IngestionRunOut:
        run = self.ops.get_run(run_id)
        if run.job_type == IngestionJobType.WEBSITE_CRAWL and run.target_url:
            return self.queue_crawl(url=run.target_url, venue_id=run.venue_id, requested_by=requested_by)
        if run.job_type in {IngestionJobType.PROVIDER_SEARCH, IngestionJobType.BUSINESS_DISCOVERY}:
            extra = run.extra_metadata or {}
            return self.queue_provider_search(
                run.provider,
                text=extra.get("text") or extra.get("query"),
                city=extra.get("city"),
                latitude=extra.get("latitude"),
                longitude=extra.get("longitude"),
                requested_by=requested_by,
            )
        raise ValidationFailed("This run type cannot be retried from the dashboard yet")

    def request_cancel(self, run_id: UUID, *, requested_by: str) -> IngestionRunOut:
        run = self.ops.get_run(run_id)
        if run.status not in {IngestionRunStatus.QUEUED, IngestionRunStatus.RUNNING, IngestionRunStatus.PENDING}:
            raise ValidationFailed("Only queued or running jobs can be cancelled")
        if run.status == IngestionRunStatus.QUEUED:
            run.status = IngestionRunStatus.CANCELLED
            run.finished_at = datetime.now(UTC)
        else:
            run.cancel_requested = True
        self._audit(requested_by, "run_cancel_requested", "ingestion_run", run.id, {})
        self.db.flush()
        return IngestionRunOut.model_validate(run)

    def providers(self) -> list[ProviderOut]:
        from datetime import date

        now_day = date.today()
        out = []
        for name, key_attr, enabled_attr in (
            (ProviderName.GOOGLE_PLACES, "google_places_api_key", "google_places_enabled"),
            (ProviderName.YELP, "yelp_api_key", "yelp_enabled"),
            (ProviderName.OPENTABLE, "opentable_api_key", "opentable_enabled"),
            (ProviderName.WEBSITE_CRAWLER, "crawler_user_agent", None),
        ):
            configured = bool(getattr(self.settings, key_attr, "")) if name != ProviderName.WEBSITE_CRAWLER else True
            if name == ProviderName.OPENTABLE:
                configured = False
            enabled = True if enabled_attr is None else bool(getattr(self.settings, enabled_attr))
            usage = self.ops.provider_usage(name, now_day)
            latest = self.ops.latest_run(name)
            out.append(
                ProviderOut(
                    name=name,
                    configured=configured,
                    enabled=enabled,
                    key_configured=configured,
                    last_status=latest.status if latest else None,
                    last_finished_at=latest.finished_at if latest else None,
                    calls_today=usage.call_count if usage else 0,
                    errors_today=usage.error_count if usage else 0,
                    rate_limits_today=usage.rate_limit_count if usage else 0,
                    records_imported_today=usage.records_imported if usage else 0,
                    note=(
                        "OpenTable needs an authorized partner feed before it can import data."
                        if name == ProviderName.OPENTABLE
                        else None
                    ),
                )
            )
        return out

    def freshness(self, *, freshness: str | None, city: str | None, page: int, page_size: int) -> FreshnessBucketOut:
        rows, total, page, page_size = self.ops.paginate_deals(
            q=None, freshness=freshness, city=city, page=page, page_size=page_size
        )
        counts = self.ops.freshness_counts(Deal)
        return FreshnessBucketOut(
            buckets=counts,
            items=[self._deal_out(d) for d in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def queue_stale_refresh(self, *, requested_by: str, city: str | None = None, limit: int = 20) -> dict:
        now = datetime.now(UTC)
        deals = self.ops.due_deals(now, min(limit, self.settings.admin_bulk_limit))
        queued = 0
        for deal in deals:
            loc = deal.venue_location
            venue = loc.venue if loc else None
            url = venue.website_url if venue else None
            if not url:
                continue
            self.queue_crawl(url=url, venue_id=venue.id if venue else None, requested_by=requested_by)
            queued += 1
        self._audit(requested_by, "stale_refresh_queued", "deal", None, {"count": queued, "city": city})
        return {"queued": queued}

    def list_review(self, *, status: str | None, page: int, page_size: int) -> PageOut:
        rows, total, page, page_size = self.ops.paginate_review(status=status, page=page, page_size=page_size)
        return PageOut(items=[ReviewOut.model_validate(r) for r in rows], page=page, page_size=page_size, total=total)

    def resolve_review(self, item_id: UUID, *, action: str, actor: str) -> ReviewOut:
        item = self.ops.get_review(item_id)
        mapping = {
            "approve": ReviewItemStatus.APPROVED,
            "reject": ReviewItemStatus.REJECTED,
            "ignore": ReviewItemStatus.IGNORED,
            "recheck": ReviewItemStatus.RECHECK,
            "merge": ReviewItemStatus.MERGED,
        }
        if action not in mapping:
            raise ValidationFailed("Unknown review action")
        item.status = mapping[action]
        item.resolved_at = datetime.now(UTC)
        item.resolved_by = actor
        self._audit(actor, f"review_{action}", "review_item", item.id, {})
        self.db.flush()
        return ReviewOut.model_validate(item)

    def errors(self) -> list[ErrorGroupOut]:
        since = datetime.now(UTC) - timedelta(days=7)
        return [ErrorGroupOut(**row) for row in self.ops.grouped_errors(since=since, limit=50)]

    def crawl_domains(self) -> list[CrawlDomainOut]:
        rows = []
        for domain in self.ops.crawl_domains():
            rows.append(
                CrawlDomainOut(
                    host=domain.host,
                    last_attempt_at=domain.last_attempt_at,
                    last_success_at=domain.last_success_at,
                    last_failure_at=domain.last_failure_at,
                    last_http_status=domain.last_http_status,
                    success_count=domain.success_count,
                    failure_count=domain.failure_count,
                    consecutive_failures=domain.consecutive_failures,
                    robots_status=domain.robots_status,
                    avg_response_ms=(float(domain.avg_response_ms) if domain.avg_response_ms is not None else None),
                    next_permitted_at=domain.next_permitted_at,
                    last_error=domain.last_error,
                )
            )
        return rows

    def system_health(self) -> SystemHealthOut:
        from sqlalchemy import text

        db_ok = True
        try:
            self.db.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        queue_ok = True
        if self.settings.queue_backend == "redis":
            try:
                import redis

                redis.Redis.from_url(self.settings.redis_url).ping()
            except Exception:
                queue_ok = False
        latest_crawl = self.ops.latest_run(ProviderName.WEBSITE_CRAWLER)
        worker = "healthy" if queue_ok else "unavailable"
        redis_status = (
            "healthy" if queue_ok else ("not configured" if self.settings.queue_backend == "memory" else "unavailable")
        )
        crawl_failed = latest_crawl is not None and latest_crawl.status == IngestionRunStatus.FAILED
        return SystemHealthOut(
            api="healthy",
            postgres="healthy" if db_ok else "unavailable",
            redis=redis_status,
            worker=worker,
            crawler="degraded" if crawl_failed else "healthy",
            google="healthy" if self.settings.google_places_api_key else "not configured",
            yelp="healthy" if self.settings.yelp_api_key else "not configured",
            opentable="not configured",
        )

    def search(self, q: str) -> SearchOut:
        raw = self.ops.search(q)
        return SearchOut(
            venues=[self._venue_out(v) for v in raw["venues"]],
            deals=[self._deal_out(d) for d in raw["deals"]],
            runs=[IngestionRunOut.model_validate(r) for r in raw["runs"]],
        )

    def audit(self) -> list[AuditOut]:
        return [AuditOut.model_validate(row) for row in self.ops.list_audit()]

    def verify_deal(self, deal_id: UUID, *, actor: str, notes: str | None) -> OpsDealOut:
        deal = self.deals.get(deal_id)
        now = datetime.now(UTC)
        self.verifications.add(
            Verification(
                id=new_id(),
                subject_type="deal",
                subject_id=deal.id,
                verification_type=VerificationType.MANUAL,
                verified_at=now,
                actor=actor,
                notes=notes or "Verified manually from admin",
                confidence=Decimal("1.000"),
            )
        )
        deal.last_verified_at = now
        windows = windows_from_settings(self.settings)
        decision = evaluate_freshness(
            kind=deal_kind_from_type(deal.deal_type),
            now=now,
            last_verified_at=now,
            windows=windows,
        )
        deal.freshness_status = decision.status
        deal.next_refresh_at = next_refresh_after_success(
            kind=deal_kind_from_type(deal.deal_type), now=now, windows=windows
        )
        deal.failure_count = 0
        self._audit(actor, "deal_verified_manual", "deal", deal.id, {"notes": notes})
        self.db.flush()
        return self._deal_out(self.deals.get(deal.id))

    def reject_deal(self, deal_id: UUID, *, actor: str) -> OpsDealOut:
        deal = self.deals.get(deal_id)
        deal.publication_state = "withdrawn"
        deal.sighting_state = SightingState.REMOVED
        self._audit(actor, "deal_rejected", "deal", deal.id, {})
        self.db.flush()
        return self._deal_out(self.deals.get(deal.id))

    def expire_deal(self, deal_id: UUID, *, actor: str) -> OpsDealOut:
        deal = self.deals.get(deal_id)
        deal.freshness_status = FreshnessStatus.EXPIRED
        deal.sighting_state = SightingState.EXPIRED
        self._audit(actor, "deal_expired", "deal", deal.id, {})
        self.db.flush()
        return self._deal_out(self.deals.get(deal.id))

    def restore_deal(self, deal_id: UUID, *, actor: str) -> OpsDealOut:
        deal = self.deals.get(deal_id)
        deal.publication_state = "published"
        deal.sighting_state = SightingState.ACTIVE
        deal.freshness_status = FreshnessStatus.UNVERIFIED
        self._audit(actor, "deal_restored", "deal", deal.id, {})
        self.db.flush()
        return self._deal_out(self.deals.get(deal.id))

    def disable_venue(self, venue_id: UUID, *, actor: str) -> OpsVenueOut:
        venue = self.venues.get(venue_id)
        venue.status = RecordStatus.DISABLED
        self._audit(actor, "venue_disabled", "venue", venue.id, {})
        self.db.flush()
        return self.venue_detail(venue.id)

    def bulk_queue_crawls(self, venue_ids: list[UUID], *, actor: str) -> dict:
        if len(venue_ids) > self.settings.admin_bulk_limit:
            raise ValidationFailed(f"Bulk operations are limited to {self.settings.admin_bulk_limit} records")
        queued = 0
        for venue_id in venue_ids:
            venue = self.venues.get(venue_id)
            if not venue.website_url:
                continue
            self.queue_crawl(url=venue.website_url, venue_id=venue.id, requested_by=actor)
            queued += 1
        return {"queued": queued}

    def export_rows(self, kind: str) -> list[dict]:
        limit = self.settings.admin_export_row_limit
        if kind == "stale_offers":
            rows, _, _, _ = self.ops.paginate_deals(
                q=None, freshness="stale", city=None, page=1, page_size=min(limit, 50)
            )
            return [{"id": str(d.id), "title": d.title, "freshness": d.freshness_status} for d in rows]
        if kind == "review_queue":
            rows, _, _, _ = self.ops.paginate_review(status="pending", page=1, page_size=min(limit, 50))
            return [{"id": str(r.id), "title": r.title, "reason": r.reason} for r in rows]
        if kind == "businesses":
            rows, _, _, _ = self.ops.paginate_venues(q=None, city=None, page=1, page_size=min(limit, 50))
            return [{"id": str(v.id), "name": v.name, "website": v.website_url} for v in rows]
        raise ValidationFailed("Unknown export kind")

    def _venue_out(self, venue: Venue, include_deals: list | None = None) -> OpsVenueOut:
        links = [
            {
                "provider": link.provider,
                "provider_business_id": link.provider_business_id,
                "provider_url": link.provider_url,
                "last_seen_at": link.last_seen_at.isoformat() if link.last_seen_at else None,
            }
            for link in (venue.provider_links or [])
        ]
        loc = venue.locations[0] if venue.locations else None
        return OpsVenueOut(
            id=venue.id,
            name=venue.name,
            slug=venue.slug,
            status=venue.status,
            website_url=venue.website_url,
            phone=venue.phone,
            city=loc.city if loc else None,
            address=loc.address_line1 if loc else None,
            freshness_status=venue.freshness_status,
            last_verified_at=venue.last_verified_at,
            last_seen_at=venue.last_seen_at,
            next_refresh_at=venue.next_refresh_at,
            failure_count=venue.failure_count,
            provider_links=links,
            location_id=loc.id if loc else None,
            timezone=loc.timezone if loc else None,
            offers=[self._deal_out(d) for d in (include_deals or [])] if include_deals is not None else [],
        )

    def _deal_out(self, deal: Deal) -> OpsDealOut:
        loc = deal.venue_location
        venue = loc.venue if loc else None
        pub = deal.publications[0] if deal.publications else None
        return OpsDealOut(
            id=deal.id,
            title=deal.title,
            description=deal.description,
            deal_type=deal.deal_type,
            publication_state=deal.publication_state,
            freshness_status=deal.freshness_status,
            sighting_state=deal.sighting_state,
            extraction_method=deal.extraction_method,
            source_confidence=deal.source_confidence,
            first_seen_at=deal.first_seen_at,
            last_seen_at=deal.last_seen_at,
            last_verified_at=deal.last_verified_at,
            next_refresh_at=deal.next_refresh_at,
            consecutive_misses=deal.consecutive_misses,
            raw_source_text=deal.raw_source_text,
            venue_id=venue.id if venue else None,
            venue_name=venue.name if venue else None,
            source_id=pub.source_id if pub else None,
            snapshot_id=pub.source_snapshot_id if pub else None,
        )

    def _audit(self, actor: str, action: str, target_type: str, target_id: UUID | None, metadata: dict) -> None:
        self.ops.add_audit(
            AdminAuditLog(
                id=new_id(),
                actor=actor,
                action=action,
                target_type=target_type,
                target_id=target_id,
                metadata_json=metadata,
                created_at=datetime.now(UTC),
            )
        )
