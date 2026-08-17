from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger("queue")

JOB_SOURCE_REFRESH = "source.refresh"
JOB_ENQUEUE_STALE = "sources.enqueue_stale"
JOB_WEBSITE_CRAWL = "website.crawl"
JOB_PROVIDER_SEARCH = "provider.search"
JOB_PROVIDER_REFRESH = "provider.refresh"
JOB_DETECT_STALE = "freshness.detect_stale"
JOB_EXPIRE_PROMOTIONS = "freshness.expire"
JOB_QUEUE_STALE_REFRESH = "freshness.queue_refresh"


@dataclass
class Job:
    id: str
    name: str
    payload: dict
    attempt: int = 0
    idempotency_key: str | None = None


class JobQueue(Protocol):
    def enqueue(self, name: str, payload: dict, *, idempotency_key: str | None = None) -> str: ...
    def dequeue(self, timeout_seconds: int = 5) -> Job | None: ...
    def ack(self, job_id: str) -> None: ...
    def fail(self, job_id: str, error: str, *, retry: bool = True) -> None: ...


class MemoryQueue:
    def __init__(self) -> None:
        self._pending: list[Job] = []
        self._inflight: dict[str, Job] = {}
        self._seen: set[str] = set()
        self._dead: list[tuple[Job, str]] = []

    def enqueue(self, name: str, payload: dict, *, idempotency_key: str | None = None) -> str:
        if idempotency_key and idempotency_key in self._seen:
            logger.info("job_deduplicated", name=name, idempotency_key=idempotency_key)
            return idempotency_key
        job = Job(id=str(uuid4()), name=name, payload=payload, idempotency_key=idempotency_key)
        self._pending.append(job)
        if idempotency_key:
            self._seen.add(idempotency_key)
        logger.info("job_enqueued", job_id=job.id, name=name)
        return job.id

    def dequeue(self, timeout_seconds: int = 5) -> Job | None:
        if not self._pending:
            time.sleep(min(timeout_seconds, 0.05))
            return None
        job = self._pending.pop(0)
        job.attempt += 1
        self._inflight[job.id] = job
        return job

    def ack(self, job_id: str) -> None:
        self._inflight.pop(job_id, None)

    def fail(self, job_id: str, error: str, *, retry: bool = True) -> None:
        job = self._inflight.pop(job_id, None)
        if job is None:
            return
        if retry and job.attempt < 5:
            job.payload = {**job.payload, "_last_error": error}
            self._pending.append(job)
            logger.info("job_requeued", job_id=job.id, attempt=job.attempt, error=error)
            return
        self._dead.append((job, error))
        logger.error("job_dead_lettered", job_id=job.id, error=error, attempt=job.attempt)


class RedisQueue:
    def __init__(self, redis_url: str) -> None:
        import redis

        self._r = redis.Redis.from_url(redis_url, decode_responses=True)
        self._queue_key = "findgood:jobs"
        self._inflight_key = "findgood:jobs:inflight"
        self._dead_key = "findgood:jobs:dead"

    def enqueue(self, name: str, payload: dict, *, idempotency_key: str | None = None) -> str:
        if idempotency_key:
            created = self._r.set(f"findgood:job:idemp:{idempotency_key}", "1", nx=True, ex=3600)
            if not created:
                logger.info("job_deduplicated", name=name, idempotency_key=idempotency_key)
                return idempotency_key
        job = Job(id=str(uuid4()), name=name, payload=payload, idempotency_key=idempotency_key)
        self._r.lpush(self._queue_key, json.dumps(job.__dict__))
        logger.info("job_enqueued", job_id=job.id, name=name)
        return job.id

    def dequeue(self, timeout_seconds: int = 5) -> Job | None:
        item = self._r.brpop(self._queue_key, timeout=timeout_seconds)
        if not item:
            return None
        data = json.loads(item[1])
        data["attempt"] = int(data.get("attempt", 0)) + 1
        self._r.hset(self._inflight_key, data["id"], json.dumps(data))
        return Job(**data)

    def ack(self, job_id: str) -> None:
        self._r.hdel(self._inflight_key, job_id)

    def fail(self, job_id: str, error: str, *, retry: bool = True) -> None:
        raw = self._r.hget(self._inflight_key, job_id)
        self._r.hdel(self._inflight_key, job_id)
        if not raw:
            return
        data = json.loads(raw)
        job = Job(**data)
        if retry and job.attempt < 5:
            delay = min(2**job.attempt, 60)
            job.payload = {**job.payload, "_last_error": error}
            # Bounded backoff without a delayed-queue module: sleep is the worker's job.
            job.payload["_retry_after_seconds"] = delay
            self._r.lpush(self._queue_key, json.dumps(job.__dict__))
            logger.info("job_requeued", job_id=job.id, attempt=job.attempt, delay=delay)
            return
        self._r.lpush(self._dead_key, json.dumps({"job": job.__dict__, "error": error}))
        logger.error("job_dead_lettered", job_id=job.id, error=error, attempt=job.attempt)


_memory_singleton: MemoryQueue | None = None


def get_queue(backend: str, redis_url: str) -> JobQueue:
    global _memory_singleton
    if backend == "memory":
        if _memory_singleton is None:
            _memory_singleton = MemoryQueue()
        return _memory_singleton
    return RedisQueue(redis_url)


def enqueue_source_refresh(queue: JobQueue, source_id: str) -> str:
    return queue.enqueue(
        JOB_SOURCE_REFRESH,
        {"source_id": source_id},
        idempotency_key=f"source.refresh:{source_id}",
    )


def enqueue_named(queue: JobQueue, name: str, payload: dict, *, idempotency_key: str | None = None) -> str:
    return queue.enqueue(name, payload, idempotency_key=idempotency_key)
