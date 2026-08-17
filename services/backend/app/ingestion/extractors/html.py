"""Heuristic offer extraction from restaurant HTML.

Order of preference:
1. JSON-LD Offer / Menu / Event blocks (structured, higher confidence)
2. Headings and nearby text that mention happy hour / specials
3. Stop. Do not invent prices or hours when the page is ambiguous.

An LLM extractor can implement the same Extractor protocol later. This module
never calls a model.
"""

from __future__ import annotations

import re
from typing import Any

from app.ingestion.crawler.html import ParsedPage
from app.ingestion.normalizers.deal import normalize_deal_type
from app.ingestion.protocols import ExtractedCandidate, ParsedDocument

HAPPY_HOUR_RE = re.compile(r"\bhappy\s*hours?\b", re.I)
SPECIALS_RE = re.compile(r"\b(daily\s+specials?|drink\s+specials?|food\s+specials?|brunch\s+specials?)\b", re.I)
TIME_RANGE_RE = re.compile(
    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:-|–|to)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|close)",
    re.I,
)
DAY_RE = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|weekdays?|weekends?|mon|tue|wed|thu|fri|sat|sun)\b",
    re.I,
)
PRICE_RE = re.compile(r"\$(\d+(?:\.\d{2})?)")


def _walk_ld(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, list):
        for item in node:
            found.extend(_walk_ld(item))
    elif isinstance(node, dict):
        graph = node.get("@graph")
        if graph:
            found.extend(_walk_ld(graph))
        else:
            found.append(node)
    return found


def _ld_offers(page: ParsedPage) -> list[ExtractedCandidate]:
    results: list[ExtractedCandidate] = []
    for block in page.json_ld:
        for node in _walk_ld(block):
            types = node.get("@type") or node.get("type") or ""
            type_text = " ".join(types) if isinstance(types, list) else str(types)
            if not re.search(r"offer|menu|event|saleevent", type_text, re.I):
                continue
            name = node.get("name") or node.get("headline")
            if not name:
                continue
            description = node.get("description")
            price = None
            if isinstance(node.get("price"), (int, float, str)):
                price = str(node["price"])
            offers = node.get("offers")
            if isinstance(offers, dict) and offers.get("price") is not None:
                price = str(offers["price"])
            payload = {
                "title": str(name)[:200],
                "description": str(description)[:2000] if description else None,
                "deal_type": normalize_deal_type(str(name)),
                "offering_kind": "both",
                "schedules": [],
                "items": ([{"name": str(name), "deal_price": price, "currency": "USD"}] if price else []),
                "raw_text": str(description or name),
                "source_url": page.canonical_url or page.url,
                "extraction_method": "structured_data",
            }
            results.append(
                ExtractedCandidate(
                    candidate_type="deal",
                    payload=payload,
                    confidence=0.82,
                    diagnostic_notes="json-ld offer/menu/event",
                )
            )
    return results


def _heuristic_offers(page: ParsedPage) -> list[ExtractedCandidate]:
    blobs: list[str] = []
    blobs.extend(page.headings)
    if page.text:
        blobs.append(page.text[:4000])
    results: list[ExtractedCandidate] = []
    seen_titles: set[str] = set()
    for blob in blobs:
        if not (HAPPY_HOUR_RE.search(blob) or SPECIALS_RE.search(blob)):
            continue
        title = HAPPY_HOUR_RE.search(blob)
        special = SPECIALS_RE.search(blob)
        label = "Happy Hour" if title else (special.group(0).title() if special else "Special")
        if label.casefold() in seen_titles:
            continue
        seen_titles.add(label.casefold())
        times = TIME_RANGE_RE.search(blob)
        days = DAY_RE.findall(blob)
        schedule: dict[str, Any] = {"days_of_week": _days(days), "ends_at_close": False}
        if times:
            schedule["start_time"] = times.group(1)
            end = times.group(2)
            if end.lower() == "close":
                schedule["ends_at_close"] = True
            else:
                schedule["end_time"] = end
        prices = PRICE_RE.findall(blob)
        items = []
        if prices:
            items.append({"name": label, "deal_price": prices[0], "currency": "USD"})
        confidence = 0.55 if times else 0.35
        if not times:
            # Schedule could not be parsed — still emit a candidate, flagged low confidence.
            pass
        payload = {
            "title": label,
            "description": blob[:500],
            "deal_type": "happy_hour" if title else "other",
            "offering_kind": "both",
            "schedules": [schedule] if schedule.get("days_of_week") or times else [],
            "items": items,
            "raw_text": blob[:1000],
            "source_url": page.canonical_url or page.url,
            "extraction_method": "heuristic",
        }
        results.append(
            ExtractedCandidate(
                candidate_type="deal",
                payload=payload,
                confidence=confidence,
                diagnostic_notes="html heuristic; times missing" if not times else "html heuristic",
            )
        )
    return results


def _days(tokens: list[str]) -> list[int]:
    mapping = {
        "monday": 1,
        "mon": 1,
        "tuesday": 2,
        "tue": 2,
        "wednesday": 3,
        "wed": 3,
        "thursday": 4,
        "thu": 4,
        "friday": 5,
        "fri": 5,
        "saturday": 6,
        "sat": 6,
        "sunday": 7,
        "sun": 7,
    }
    days: set[int] = set()
    for token in tokens:
        key = token.casefold()
        if key.startswith("weekday"):
            days.update({1, 2, 3, 4, 5})
        elif key.startswith("weekend"):
            days.update({6, 7})
        elif key in mapping:
            days.add(mapping[key])
    return sorted(days)


class HtmlOfferExtractor:
    version = "html-offer-1"

    def extract(self, document: ParsedDocument) -> list[ExtractedCandidate]:
        page = document.data
        if not isinstance(page, ParsedPage):
            return []
        structured = _ld_offers(page)
        if structured:
            return structured
        return _heuristic_offers(page)
