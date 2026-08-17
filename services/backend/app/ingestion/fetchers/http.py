"""Production HTTP fetcher.

Adds retries, validated redirects, robots.txt, and per-domain rate limiting
on top of the shared outbound client. Fetchers still return bytes only.
"""

from urllib.parse import urlparse

from app.ingestion.crawler.rate_limit import CrawlRateLimiter
from app.ingestion.crawler.robots import RobotsChecker
from app.ingestion.http import OutboundHttpClient
from app.ingestion.protocols import FetchResult
from app.ingestion.safety import UnsafeURLError, assert_public_http_url


class HttpFetcher:
    def __init__(
        self,
        *,
        max_bytes: int,
        timeout_seconds: int,
        user_agent: str,
        client: OutboundHttpClient | None = None,
        robots: RobotsChecker | None = None,
        rate_limiter: CrawlRateLimiter | None = None,
        respect_robots: bool = True,
        allowed_content_types: list[str] | None = None,
    ) -> None:
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent
        self.client = client or OutboundHttpClient(
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        self.robots = robots
        self.rate_limiter = rate_limiter
        self.respect_robots = respect_robots
        self.allowed_content_types = allowed_content_types or [
            "text/html",
            "application/xhtml+xml",
            "application/json",
            "text/plain",
        ]

    def fetch(self, url: str, *, user_agent: str, timeout_seconds: int) -> FetchResult:
        assert_public_http_url(url)
        if self.respect_robots and self.robots is not None and not self.robots.allowed(url):
            return FetchResult(
                url=url,
                http_status=0,
                content_type="",
                content=b"",
                skipped_reason="robots_disallow",
            )
        host = (urlparse(url).hostname or "").casefold()
        if self.rate_limiter:
            self.rate_limiter.acquire(host)
        try:
            result = self.client.get(url, timeout_seconds=min(timeout_seconds, self.timeout_seconds))
        finally:
            if self.rate_limiter:
                self.rate_limiter.release(host)
        content_type = (result.content_type or "").split(";")[0].strip().casefold()
        if content_type and not any(content_type.startswith(allowed) for allowed in self.allowed_content_types):
            raise UnsafeURLError(f"Content type not allowed: {content_type}")
        return result
