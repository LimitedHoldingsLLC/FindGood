import httpx

from app.ingestion.protocols import FetchResult
from app.ingestion.safety import UnsafeURLError, assert_public_http_url


class HttpFetcher:
    def __init__(self, *, max_bytes: int, timeout_seconds: int, user_agent: str) -> None:
        self.max_bytes = max_bytes
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def fetch(self, url: str, *, user_agent: str, timeout_seconds: int) -> FetchResult:
        assert_public_http_url(url)
        timeout = min(timeout_seconds, self.timeout_seconds)
        headers = {"User-Agent": user_agent or self.user_agent}
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            response = client.get(url, headers=headers)
            if 300 <= response.status_code < 400:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeURLError("Redirect without Location")
                assert_public_http_url(str(httpx.URL(url).join(location)))
                raise UnsafeURLError("Redirects must be re-validated; refusing automatic follow")
            content = response.content[: self.max_bytes + 1]
            if len(content) > self.max_bytes:
                raise ValueError("Response exceeded bounded size")
            return FetchResult(
                url=url,
                http_status=response.status_code,
                content_type=response.headers.get("content-type", "application/octet-stream"),
                content=content,
                headers={"content-type": response.headers.get("content-type", "")},
            )
