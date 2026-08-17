import httpx
import pytest
from app.ingestion.crawler.discovery import discover_internal_links, prioritize_urls
from app.ingestion.crawler.html import parse_html
from app.ingestion.crawler.robots import RobotsChecker
from app.ingestion.extractors.html import HtmlOfferExtractor
from app.ingestion.fetchers.http import HttpFetcher
from app.ingestion.http import OutboundHttpClient
from app.ingestion.parsers.html_parser import HtmlParser
from app.ingestion.protocols import FetchResult
from app.ingestion.safety import UnsafeURLError


def _client(handler) -> OutboundHttpClient:
    return OutboundHttpClient(
        user_agent="FindGoodBot/1.0",
        timeout_seconds=2,
        max_bytes=50_000,
        retry_count=2,
        transport=httpx.MockTransport(handler),
        validate_url=False,
    )


def test_robots_disallow() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private\n")
        return httpx.Response(200, text="ok")

    client = _client(handler)
    robots = RobotsChecker(client, user_agent="FindGoodBot/1.0")
    assert robots.allowed("https://example.com/menu") is True
    assert robots.allowed("https://example.com/private/secret") is False


def test_html_extraction_and_json_ld() -> None:
    html = """
    <html><head><title>Nightbird</title>
    <script type="application/ld+json">
    {"@type": "Offer", "name": "Happy Hour", "description": "Cocktails $8", "offers": {"price": "8"}}
    </script></head>
    <body><h1>Happy Hour</h1><p>Weekdays 4pm-6pm</p></body></html>
    """
    page = parse_html(html, url="https://nightbird.example/happy-hour")
    assert page.title == "Nightbird"
    assert page.json_ld
    parsed = HtmlParser().parse(
        FetchResult(
            url="https://nightbird.example",
            http_status=200,
            content_type="text/html",
            content=html.encode(),
        )
    )
    extracted = HtmlOfferExtractor().extract(parsed)
    assert extracted
    assert "Happy Hour" in extracted[0].payload["title"]


def test_internal_link_discovery_and_page_limit() -> None:
    html = """
    <a href="/happy-hour">HH</a>
    <a href="/menu">Menu</a>
    <a href="https://other.com/x">external</a>
    <a href="/about">About</a>
    """
    links = discover_internal_links(html, "https://restaurant.example/")
    assert any("happy-hour" in item for item in links)
    assert all("other.com" not in item for item in links)
    limited = prioritize_urls("https://restaurant.example/", links, max_pages=2)
    assert len(limited) == 2
    assert limited[0] == "https://restaurant.example/"


def test_retries_on_500_then_succeeds() -> None:
    hits = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        if hits["n"] < 2:
            return httpx.Response(500, text="nope")
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    client = _client(handler)
    result = client.get("https://example.com/menu")
    assert result.http_status == 200
    assert result.retry_count >= 1


def test_retries_on_429() -> None:
    hits = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        if hits["n"] < 2:
            return httpx.Response(429, text="slow")
        return httpx.Response(200, text="ok", headers={"content-type": "text/plain"})

    result = _client(handler).get("https://example.com/menu")
    assert result.http_status == 200


def test_http_fetcher_skips_robots() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        return httpx.Response(200, text="should not fetch")

    client = _client(handler)
    robots = RobotsChecker(client, user_agent="FindGoodBot/1.0")
    fetcher = HttpFetcher(
        max_bytes=1000,
        timeout_seconds=2,
        user_agent="FindGoodBot/1.0",
        client=client,
        robots=robots,
        respect_robots=True,
        allowed_content_types=["text/html", "text/plain"],
    )
    result = fetcher.fetch("https://example.com/menu", user_agent="FindGoodBot/1.0", timeout_seconds=2)
    assert result.skipped_reason == "robots_disallow"


def test_disallowed_content_type() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})

    fetcher = HttpFetcher(
        max_bytes=1000,
        timeout_seconds=2,
        user_agent="FindGoodBot/1.0",
        client=_client(handler),
        respect_robots=False,
        allowed_content_types=["text/html"],
    )
    with pytest.raises(UnsafeURLError):
        fetcher.fetch("https://example.com/file.pdf", user_agent="x", timeout_seconds=2)
