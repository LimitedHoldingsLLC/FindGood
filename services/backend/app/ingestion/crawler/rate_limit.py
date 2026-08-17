"""Global and per-domain crawl rate limiting.

In-process semaphores stop one worker from opening too many sockets.
Redis (when available) coordinates multiple workers so they do not all hit
the same restaurant website at once.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from app.core.logging import get_logger

logger = get_logger("rate_limit")


class CrawlRateLimiter:
    def __init__(
        self,
        *,
        global_concurrency: int = 10,
        domain_concurrency: int = 1,
        per_domain_delay_seconds: float = 1.0,
        redis_client: Any | None = None,
    ) -> None:
        self.global_sema = threading.Semaphore(max(global_concurrency, 1))
        self.domain_concurrency = max(domain_concurrency, 1)
        self.per_domain_delay_seconds = per_domain_delay_seconds
        self._domain_semas: dict[str, threading.Semaphore] = defaultdict(
            lambda: threading.Semaphore(self.domain_concurrency)
        )
        self._last_request: dict[str, float] = {}
        self._lock = threading.Lock()
        self._redis = redis_client

    def acquire(self, host: str) -> None:
        host_key = host.casefold()
        self.global_sema.acquire()
        self._domain_semas[host_key].acquire()
        self._wait_delay(host_key)
        self._wait_redis(host_key)

    def release(self, host: str) -> None:
        host_key = host.casefold()
        with self._lock:
            self._last_request[host_key] = time.monotonic()
        self._domain_semas[host_key].release()
        self.global_sema.release()

    def _wait_delay(self, host: str) -> None:
        with self._lock:
            last = self._last_request.get(host, 0.0)
        wait = self.per_domain_delay_seconds - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)

    def _wait_redis(self, host: str) -> None:
        if self._redis is None:
            return
        key = f"findgood:crawl:domain:{host}"
        try:
            # One slot per domain delay window across workers.
            created = self._redis.set(key, "1", nx=True, px=int(self.per_domain_delay_seconds * 1000) or 1)
            while not created:
                time.sleep(min(self.per_domain_delay_seconds, 0.25))
                created = self._redis.set(key, "1", nx=True, px=int(self.per_domain_delay_seconds * 1000) or 1)
        except Exception:
            logger.info("rate_limit_redis_unavailable", host=host)
