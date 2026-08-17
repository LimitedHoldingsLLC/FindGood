"""Interpret whether a previously published offer is still on its source page.

last_seen_at means: the source still contained this offer during the latest look.
last_verified_at means: we had enough evidence to treat it as currently valid.

A failed fetch is not a disappearance. Missing text on a successful fetch is a miss,
not an instant delete.
"""

from __future__ import annotations

import re

from app.db.models.enums import SightingState

_WS = re.compile(r"\s+")


def collapse(value: str) -> str:
    return _WS.sub(" ", value).casefold().strip()


def offer_appears_on_page(*, title: str, raw_source_text: str | None, page_text: str) -> bool:
    """Return True only when the page still contains recognizable offer text.

    Short titles are ignored so words like "Menu" do not count as proof.
    """
    haystack = collapse(page_text)
    if not haystack:
        return False
    needle = collapse(title)
    if len(needle) >= 6 and needle in haystack:
        return True
    snippet = collapse(raw_source_text or "")
    if 12 <= len(snippet) <= 400 and snippet[:80] in haystack:
        return True
    return False


def next_sighting_after_miss(consecutive_misses: int) -> str:
    """Move an offer toward removed after repeated successful crawls that lack it.

    1 miss → not_seen_once
    2 misses → verification_needed (review queue)
    3+ misses → removed (hidden from consumers, still in the database)
    """
    if consecutive_misses <= 1:
        return SightingState.NOT_SEEN_ONCE
    if consecutive_misses == 2:
        return SightingState.VERIFICATION_NEEDED
    return SightingState.REMOVED
