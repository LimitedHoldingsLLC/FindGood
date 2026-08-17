"""robots.txt fetch, parse, and cache.

If a restaurant asks us not to crawl a path, we skip it and log why.
We never try to sneak around robots, logins, CAPTCHAs, or paywalls.
"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from app.core.logging import get_logger
from app.ingestion.http import OutboundHttpClient
from app.ingestion.safety import UnsafeURLError, assert_public_http_url

logger = get_logger("robots")


class RobotsChecker:
    def __init__(
        self,
        client: OutboundHttpClient,
        *,
        user_agent: str,
        cache_ttl_seconds: int = 3600,
        enabled: bool = True,
    ) -> None:
        self.client = client
        self.user_agent = user_agent
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enabled = enabled
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}

    def allowed(self, url: str) -> bool:
        if not self.enabled:
            return True
        parsed = urlparse(url)
        host = (parsed.hostname or "").casefold()
        if not host:
            return False
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        parser = self._parser_for(host, robots_url)
        if parser is None:
            # Unreachable or invalid robots.txt: we still crawl public pages,
            # but a later fetch can fail on its own.
            return True
        try:
            return parser.can_fetch(self.user_agent, url)
        except Exception:
            return True

    def _parser_for(self, host: str, robots_url: str) -> RobotFileParser | None:
        cached = self._cache.get(host)
        now = time.time()
        if cached and now - cached[0] < self.cache_ttl_seconds:
            return cached[1]
        parser: RobotFileParser | None = None
        try:
            assert_public_http_url(robots_url)
            fetched = self.client.get(robots_url, validate_url=True)
            if fetched.http_status == 200 and fetched.content:
                parser = RobotFileParser()
                parser.parse(fetched.content.decode("utf-8", errors="replace").splitlines())
            else:
                parser = None
        except (UnsafeURLError, Exception) as exc:
            logger.info("robots_fetch_skipped", host=host, error=exc.__class__.__name__)
            parser = None
        self._cache[host] = (now, parser)
        return parser
