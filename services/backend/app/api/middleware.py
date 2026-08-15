import time
from collections import defaultdict, deque
from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import bind_request_id, get_logger, new_request_id

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        bind_request_id(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed", path=request.url.path, method=request.method)
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        return response


class InMemoryRateLimiter(BaseHTTPMiddleware):
    """Hook for request-rate limiting. Replace with Redis later if needed."""

    def __init__(self, app, *, enabled: bool, per_minute: int) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.per_minute = per_minute
        self._hits: dict[str, deque[datetime]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or request.url.path in {"/health", "/ready"}:
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = datetime.now(UTC)
        bucket = self._hits[key]
        cutoff = now.timestamp() - 60
        while bucket and bucket[0].timestamp() < cutoff:
            bucket.popleft()
        if len(bucket) >= self.per_minute:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests"}},
            )
        bucket.append(now)
        return await call_next(request)
