"""Exact-signal duplicate matching for venues.

A restaurant can show up in Google, Yelp, OpenTable, and its own website.
We only auto-merge when independent strong signals agree. Similar names alone
are never enough — two "Joe's Pizza" shops in different cities are not the same.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from urllib.parse import urlparse

from app.domain.geo import optional_haversine_km

AUTO_MERGE_SCORE = 0.85
REVIEW_SCORE = 0.5
NEARBY_METERS_STRONG = 75
NEARBY_METERS_PHONE = 150


@dataclass(frozen=True)
class VenueIdentity:
    id: str
    name: str
    city: str
    phone: str | None
    website_url: str | None
    latitude: Decimal | None
    longitude: Decimal | None
    address_line1: str | None = None


@dataclass(frozen=True)
class DuplicateMatch:
    entity_id: str
    score: float
    reasons: list[str]


class DuplicateMatcher(Protocol):
    def match_venues(self, candidate: VenueIdentity, existing: list[VenueIdentity]) -> list[DuplicateMatch]: ...


MatchDecision = Literal["auto_merge", "review", "new"]


def _norm_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _norm_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits or None


def _norm_host(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    return host or None


def _norm_address(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = " ".join(value.casefold().replace(",", " ").split())
    for token in (" street", " st", " avenue", " ave", " boulevard", " blvd", " road", " rd", " drive", " dr"):
        cleaned = cleaned.replace(token, "")
    return cleaned or None


class SimpleDuplicateMatcher:
    """Exact identity signals only. Fuzzy name matching stays out of this class on purpose."""

    def match_venues(self, candidate: VenueIdentity, existing: list[VenueIdentity]) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        cand_name = _norm_name(candidate.name)
        cand_phone = _norm_phone(candidate.phone)
        cand_host = _norm_host(candidate.website_url)
        cand_city = _norm_name(candidate.city)
        cand_address = _norm_address(candidate.address_line1)
        for venue in existing:
            reasons: list[str] = []
            score = 0.0
            same_city = cand_city == _norm_name(venue.city)
            km = optional_haversine_km(candidate.latitude, candidate.longitude, venue.latitude, venue.longitude)
            nearby_strong = km is not None and km <= (NEARBY_METERS_STRONG / 1000)
            nearby_phone = km is not None and km <= (NEARBY_METERS_PHONE / 1000)

            if cand_name and cand_name == _norm_name(venue.name) and same_city:
                reasons.append("normalized_name_and_city")
                score += 0.6
            if cand_phone and cand_phone == _norm_phone(venue.phone):
                reasons.append("phone")
                score += 0.3
            if cand_host and cand_host == _norm_host(venue.website_url):
                reasons.append("website")
                score += 0.3
            if cand_address and cand_address == _norm_address(venue.address_line1) and same_city:
                reasons.append("normalized_address")
                score += 0.25
            if nearby_strong and cand_name and cand_name == _norm_name(venue.name):
                reasons.append("nearby_same_name")
                score += 0.25
            elif nearby_phone and "phone" in reasons:
                reasons.append("nearby_phone")
                score += 0.1

            if reasons:
                matches.append(DuplicateMatch(entity_id=venue.id, score=min(score, 1.0), reasons=reasons))
        return sorted(matches, key=lambda item: item.score, reverse=True)


def classify_match(match: DuplicateMatch | None) -> MatchDecision:
    """Auto-merge only with independent strong signals. Name+city alone goes to review."""
    if match is None:
        return "new"
    reasons = set(match.reasons)
    strong = {"phone", "website", "normalized_address", "nearby_same_name"}
    if match.score >= AUTO_MERGE_SCORE and (reasons & strong):
        return "auto_merge"
    if "phone" in reasons and ("website" in reasons or "nearby_phone" in reasons or "nearby_same_name" in reasons):
        return "auto_merge"
    if "website" in reasons and "nearby_same_name" in reasons:
        return "auto_merge"
    if match.score >= REVIEW_SCORE:
        return "review"
    return "new"
