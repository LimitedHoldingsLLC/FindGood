"""Discover a small set of useful pages from a restaurant homepage.

We do not walk an entire website. We prefer URLs whose path looks like a
menu, happy hour, specials, drinks, events, or locations page, and we stop
at configured depth and page-count limits.
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

PRIORITY_TOKENS = (
    "happy-hour",
    "happyhour",
    "specials",
    "deals",
    "menu",
    "menus",
    "drinks",
    "bar",
    "events",
    "offers",
    "promotions",
    "locations",
)


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


def link_priority(url: str) -> int:
    path = urlparse(url).path.casefold()
    score = 0
    for index, token in enumerate(PRIORITY_TOKENS):
        if token in path:
            score += len(PRIORITY_TOKENS) - index
    return score


def same_host(left: str, right: str) -> bool:
    a = (urlparse(left).hostname or "").casefold()
    b = (urlparse(right).hostname or "").casefold()
    if a.startswith("www."):
        a = a[4:]
    if b.startswith("www."):
        b = b[4:]
    return bool(a) and a == b


def discover_internal_links(html: str, base_url: str) -> list[str]:
    collector = _LinkCollector()
    try:
        collector.feed(html)
        collector.close()
    except Exception:
        return []
    seen: set[str] = set()
    found: list[str] = []
    for href in collector.hrefs:
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if not same_host(base_url, absolute):
            continue
        cleaned = parsed._replace(fragment="", query="").geturl()
        if cleaned in seen:
            continue
        seen.add(cleaned)
        found.append(cleaned)
    found.sort(key=link_priority, reverse=True)
    return found


def prioritize_urls(start_url: str, discovered: list[str], *, max_pages: int) -> list[str]:
    ordered = [start_url]
    for url in discovered:
        if url.rstrip("/") == start_url.rstrip("/"):
            continue
        ordered.append(url)
        if len(ordered) >= max_pages:
            break
    return ordered
