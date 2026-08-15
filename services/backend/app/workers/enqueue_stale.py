"""Cron entrypoint. Enqueues work; contains no ingestion business logic.

python -m app.workers.enqueue_stale
"""

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.repositories.source_repository import SourceRepository
from app.db.session import SessionLocal
from app.workers.queue import enqueue_source_refresh, get_queue

logger = get_logger("cron")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_format, settings.log_level)
    queue = get_queue(settings.queue_backend, settings.redis_url)
    db = SessionLocal()
    try:
        sources = SourceRepository(db).stale_sources()
        for source in sources:
            enqueue_source_refresh(queue, str(source.id))
        logger.info("cron_enqueued_stale_sources", count=len(sources))
    finally:
        db.close()


if __name__ == "__main__":
    main()
