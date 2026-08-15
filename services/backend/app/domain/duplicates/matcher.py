from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from urllib.parse import urlparse


@dataclass(frozen=True)
class VenueIdentity:
    id: str
    name: str
    city: str
    phone: str | None
    website_url: str | None
    latitude: Decimal | None
    longitude: Decimal | None


@dataclass(frozen=True)
class DuplicateMatch:
    entity_id: str
    score: float
    reasons: list[str]


class DuplicateMatcher(Protocol):
    def match_venues(self, candidate: VenueIdentity, existing: list[VenueIdentity]) -> list[DuplicateMatch]: ...


def _norm_name(value: str) -> str:
    return " ".join(value.casefold().split())


def _norm_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None


def _norm_host(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    return host or None


class SimpleDuplicateMatcher:
    """Exact identity signals only. Fuzzy matching is a later concern."""

    def match_venues(self, candidate: VenueIdentity, existing: list[VenueIdentity]) -> list[DuplicateMatch]:
        matches: list[DuplicateMatch] = []
        cand_name = _norm_name(candidate.name)
        cand_phone = _norm_phone(candidate.phone)
        cand_host = _norm_host(candidate.website_url)
        cand_city = _norm_name(candidate.city)
        for venue in existing:
            reasons: list[str] = []
            score = 0.0
            if cand_name and cand_name == _norm_name(venue.name) and cand_city == _norm_name(venue.city):
                reasons.append("normalized_name_and_city")
                score += 0.6
            if cand_phone and cand_phone == _norm_phone(venue.phone):
                reasons.append("phone")
                score += 0.3
            if cand_host and cand_host == _norm_host(venue.website_url):
                reasons.append("website")
                score += 0.3
            if reasons:
                matches.append(DuplicateMatch(entity_id=venue.id, score=min(score, 1.0), reasons=reasons))
        return sorted(matches, key=lambda item: item.score, reverse=True)
