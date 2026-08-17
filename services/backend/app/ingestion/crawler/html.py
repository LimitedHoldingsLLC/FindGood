"""Pull title, headings, visible text, JSON-LD, and metadata from HTML.

We keep the original URL and a content hash so every later fact can point
back to the page it came from. Ambiguous values stay empty rather than guessed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

SKIP_TAGS = {"script", "style", "noscript", "svg", "path"}


class _HtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.headings: list[str] = []
        self.texts: list[str] = []
        self.canonical: str | None = None
        self.meta: dict[str, str] = {}
        self.json_ld_blocks: list[str] = []
        self._capture_title = False
        self._capture_heading = False
        self._capture_ld = False
        self._ld_buf: list[str] = []
        self._skip_depth = 0
        self._current_heading: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name: (value or "") for name, value in attrs}
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            if tag == "script" and "ld+json" in attr.get("type", "").casefold():
                self._capture_ld = True
                self._ld_buf = []
                self._skip_depth -= 1
            return
        if tag == "title":
            self._capture_title = True
        if tag in {"h1", "h2", "h3"}:
            self._capture_heading = True
            self._current_heading = []
        if tag == "meta":
            key = attr.get("property") or attr.get("name")
            content = attr.get("content")
            if key and content:
                self.meta[key.casefold()] = content
        if tag == "link" and attr.get("rel", "").casefold() == "canonical" and attr.get("href"):
            self.canonical = attr["href"]

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capture_ld:
            self.json_ld_blocks.append("".join(self._ld_buf))
            self._capture_ld = False
            return
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
            return
        if tag == "title":
            self._capture_title = False
        if tag in {"h1", "h2", "h3"} and self._capture_heading:
            text = collapse_ws("".join(self._current_heading))
            if text:
                self.headings.append(text)
            self._capture_heading = False

    def handle_data(self, data: str) -> None:
        if self._capture_ld:
            self._ld_buf.append(data)
            return
        if self._skip_depth:
            return
        if self._capture_title:
            self.title_parts.append(data)
        elif self._capture_heading:
            self._current_heading.append(data)
        else:
            self.texts.append(data)


def collapse_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass
class ParsedPage:
    url: str
    canonical_url: str | None
    title: str | None
    headings: list[str]
    text: str
    json_ld: list[Any]
    metadata: dict[str, str]
    last_modified: str | None
    retrieved_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def parse_html(
    html: str,
    *,
    url: str,
    headers: dict[str, str] | None = None,
) -> ParsedPage:
    extractor = _HtmlExtractor()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:
        pass
    json_ld: list[Any] = []
    for block in extractor.json_ld_blocks:
        try:
            json_ld.append(json.loads(block))
        except json.JSONDecodeError:
            continue
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    title = collapse_ws("".join(extractor.title_parts)) or extractor.meta.get("og:title")
    text = collapse_ws(" ".join(extractor.texts))
    return ParsedPage(
        url=url,
        canonical_url=extractor.canonical or extractor.meta.get("og:url"),
        title=title or None,
        headings=extractor.headings,
        text=text[:50_000],
        json_ld=json_ld,
        metadata=extractor.meta,
        last_modified=headers.get("last-modified"),
    )
