"""Shared outbound HTTP client for crawlers and provider APIs.

One client owns timeouts, size caps, redirects (re-checked for SSRF), retries,
and the FindGood user agent. Callers should not create ad-hoc httpx clients.
"""

from __future__ import annotations

import random
import time

import httpx

from app.core.logging import get_logger
from app.ingestion.protocols import FetchResult
from app.ingestion.safety import UnsafeURLError, assert_public_http_url

logger = get_logger("http")

RETRY_STATUS = {429, 500, 502, 503, 504}
TRANSIENT_ERRORS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
)


def _sleep_backoff(attempt: int) -> None:
    # Exponential backoff with a little jitter so many workers do not retry in lockstep.
    base = min(2**attempt, 30)
    time.sleep(base * (0.5 + random.random()))


class OutboundHttpClient:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout_seconds: int,
        max_bytes: int,
        max_redirects: int = 3,
        retry_count: int = 3,
        transport: httpx.BaseTransport | None = None,
        validate_url: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.retry_count = retry_count
        self.validate_url = validate_url
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": user_agent},
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
        validate_url: bool | None = None,
    ) -> FetchResult:
        return self._request(
            "GET",
            url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            validate_url=self.validate_url if validate_url is None else validate_url,
        )

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
        timeout_seconds: int | None = None,
        validate_url: bool | None = None,
    ) -> FetchResult:
        return self._request(
            "POST",
            url,
            headers=headers,
            json_body=json_body,
            timeout_seconds=timeout_seconds,
            validate_url=self.validate_url if validate_url is None else validate_url,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None,
        json_body: dict | None = None,
        timeout_seconds: int | None,
        validate_url: bool,
    ) -> FetchResult:
        current = url
        timeout = timeout_seconds or self.timeout_seconds
        merged = {"User-Agent": self.user_agent, **(headers or {})}
        retries = 0
        redirects = 0
        started = time.perf_counter()
        while True:
            if validate_url:
                assert_public_http_url(current)
            try:
                response = self._client.request(
                    method,
                    current,
                    headers=merged,
                    json=json_body,
                    timeout=timeout,
                )
            except TRANSIENT_ERRORS as exc:
                if retries >= self.retry_count:
                    raise
                retries += 1
                logger.info("http_retry", url=current, attempt=retries, error=exc.__class__.__name__)
                _sleep_backoff(retries)
                continue
            if 300 <= response.status_code < 400:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeURLError("Redirect without Location")
                nxt = str(httpx.URL(current).join(location))
                if validate_url:
                    assert_public_http_url(nxt)
                redirects += 1
                if redirects > self.max_redirects:
                    raise UnsafeURLError("Too many redirects")
                current = nxt
                method = "GET"
                json_body = None
                continue
            if response.status_code in RETRY_STATUS and retries < self.retry_count:
                retries += 1
                logger.info(
                    "http_retry_status",
                    url=current,
                    status=response.status_code,
                    attempt=retries,
                )
                _sleep_backoff(retries)
                continue
            content = response.content[: self.max_bytes + 1]
            if len(content) > self.max_bytes:
                raise ValueError("Response exceeded bounded size")
            header_map = {k.lower(): v for k, v in response.headers.items()}
            duration_ms = int((time.perf_counter() - started) * 1000)
            return FetchResult(
                url=url,
                http_status=response.status_code,
                content_type=header_map.get("content-type", "application/octet-stream"),
                content=content,
                headers=header_map,
                final_url=str(response.url) if response.url else current,
                retry_count=retries,
                duration_ms=duration_ms,
            )
