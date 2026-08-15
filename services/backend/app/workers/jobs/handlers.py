from uuid import UUID

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.ingestion.pipeline import IngestionPipeline
from app.workers.queue import (
    JOB_ENQUEUE_STALE,
    JOB_SOURCE_REFRESH,
    Job,
    JobQueue,
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
        logger.info("stale_sources_enqueued", count=len(sources))
    finally:
        db.close()
