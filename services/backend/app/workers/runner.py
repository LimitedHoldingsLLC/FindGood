"""Independently runnable worker process.

python -m app.workers.runner
"""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.workers.jobs.handlers import handle_job
from app.workers.queue import get_queue

logger = get_logger("worker")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_format, settings.log_level)
    queue = get_queue(settings.queue_backend, settings.redis_url)
    logger.info("worker_started", queue_backend=settings.queue_backend)
    while True:
        job = queue.dequeue(timeout_seconds=5)
        if job is None:
            continue
        retry_after = job.payload.get("_retry_after_seconds")
        if retry_after:
            time.sleep(min(int(retry_after), 60))
        try:
            handle_job(job, queue, settings)
            queue.ack(job.id)
            logger.info("job_succeeded", job_id=job.id, name=job.name, attempt=job.attempt)
        except Exception as exc:
            logger.exception("job_failed", job_id=job.id, name=job.name, attempt=job.attempt)
            queue.fail(job.id, str(exc), retry=True)


if __name__ == "__main__":
    main()
