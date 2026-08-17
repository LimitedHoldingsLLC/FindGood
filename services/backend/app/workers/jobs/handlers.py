from uuid import UUID

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.ingestion.orchestrator import IngestionOrchestrator
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.providers.base import ProviderSearchQuery
from app.services.freshness_jobs import detect_and_mark_stale, expire_finished_promotions
from app.workers.queue import (
    JOB_DETECT_STALE,
    JOB_ENQUEUE_STALE,
    JOB_EXPIRE_PROMOTIONS,
    JOB_PROVIDER_REFRESH,
    JOB_PROVIDER_SEARCH,
    JOB_QUEUE_STALE_REFRESH,
    JOB_SOURCE_REFRESH,
    JOB_WEBSITE_CRAWL,
    Job,
    JobQueue,
    enqueue_named,
    enqueue_source_refresh,
)

logger = get_logger("jobs")


def handle_job(job: Job, queue: JobQueue, settings: Settings) -> None:
    if job.name == JOB_SOURCE_REFRESH:
        _refresh_source(job.payload["source_id"], settings, attempt=job.attempt)
        return
    if job.name == JOB_ENQUEUE_STALE:
        _enqueue_stale(queue)
        return
    if job.name == JOB_WEBSITE_CRAWL:
        _website_crawl(job.payload, settings)
        return
    if job.name == JOB_PROVIDER_SEARCH:
        _provider_search(job.payload, settings)
        return
    if job.name == JOB_PROVIDER_REFRESH:
        _provider_refresh(job.payload, settings)
        return
    if job.name == JOB_DETECT_STALE:
        _detect_stale(settings)
        return
    if job.name == JOB_EXPIRE_PROMOTIONS:
        _expire(settings)
        return
    if job.name == JOB_QUEUE_STALE_REFRESH:
        _queue_stale_refresh(queue, settings)
        return
    raise ValueError(f"Unknown job: {job.name}")


def _refresh_source(source_id: str, settings: Settings, *, attempt: int) -> None:
    db = SessionLocal()
    try:
        pipeline = IngestionPipeline(db, settings)
        pipeline.run(UUID(source_id), retry_count=max(attempt - 1, 0))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _enqueue_stale(queue: JobQueue) -> None:
    from app.db.repositories.source_repository import SourceRepository

    db = SessionLocal()
    try:
        sources = SourceRepository(db).stale_sources()
        for source in sources:
            enqueue_source_refresh(queue, str(source.id))
        enqueue_named(queue, JOB_DETECT_STALE, {})
        enqueue_named(queue, JOB_EXPIRE_PROMOTIONS, {})
        logger.info("stale_sources_enqueued", count=len(sources))
    finally:
        db.close()


def _website_crawl(payload: dict, settings: Settings) -> None:
    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db, settings)
        run = None
        if payload.get("run_id"):
            from app.db.models import IngestionRun

            run = db.get(IngestionRun, UUID(payload["run_id"]))
        venue_id = UUID(payload["venue_id"]) if payload.get("venue_id") else None
        orchestrator.crawl_url(
            payload["url"],
            requested_by=payload.get("requested_by") or "worker",
            venue_id=venue_id,
            run=run,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _provider_search(payload: dict, settings: Settings) -> None:
    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db, settings)
        run = None
        if payload.get("run_id"):
            from app.db.models import IngestionRun

            run = db.get(IngestionRun, UUID(payload["run_id"]))
        query = ProviderSearchQuery(
            text=payload.get("text"),
            city=payload.get("city"),
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
        )
        orchestrator.search_provider(
            payload["provider"],
            query,
            requested_by=payload.get("requested_by") or "worker",
            run=run,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _provider_refresh(payload: dict, settings: Settings) -> None:
    db = SessionLocal()
    try:
        orchestrator = IngestionOrchestrator(db, settings)
        orchestrator.refresh_provider_venue(
            payload["provider"],
            UUID(payload["venue_id"]),
            requested_by=payload.get("requested_by") or "worker",
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _detect_stale(settings: Settings) -> None:
    db = SessionLocal()
    try:
        detect_and_mark_stale(db, settings)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _expire(settings: Settings) -> None:
    db = SessionLocal()
    try:
        expire_finished_promotions(db, settings)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _queue_stale_refresh(queue: JobQueue, settings: Settings) -> None:
    from app.db.repositories.ops_repository import OpsRepository

    db = SessionLocal()
    try:
        from datetime import UTC, datetime

        ops = OpsRepository(db)
        for venue in ops.due_venues(datetime.now(UTC), 50):
            if venue.website_url:
                enqueue_named(
                    queue,
                    JOB_WEBSITE_CRAWL,
                    {"url": venue.website_url, "venue_id": str(venue.id), "requested_by": "scheduler"},
                    idempotency_key=f"stale-crawl:{venue.id}",
                )
    finally:
        db.close()
