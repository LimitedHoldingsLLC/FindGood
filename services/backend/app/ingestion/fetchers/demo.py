from pathlib import Path

from app.ingestion.protocols import FetchResult

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class DemoFetcher:
    """Deterministic local adapter. Never opens a network connection."""

    def fetch(self, url: str, *, user_agent: str, timeout_seconds: int) -> FetchResult:
        if not url.startswith("demo://"):
            raise ValueError("DemoFetcher only accepts demo:// URLs")
        slug = url.removeprefix("demo://").strip("/")
        path = FIXTURE_DIR / f"{slug}.json"
        if not path.exists():
            raise FileNotFoundError(f"Demo fixture not found: {slug}")
        content = path.read_bytes()
        return FetchResult(
            url=url,
            http_status=200,
            content_type="application/json",
            content=content,
            headers={"user-agent": user_agent, "x-timeout": str(timeout_seconds)},
        )
