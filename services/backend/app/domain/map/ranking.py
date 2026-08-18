"""Pick one pin per location and rank it for the current query.

Several offers can live at the same restaurant. The map shows one marker.
This ranking is explainable: active now beats later, fresh beats aging,
then deal value. Google stars are not a signal here.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.domain.deals.money import savings
from app.domain.schedules.engine import AvailabilityStatus, DealAvailability

_AVAIL = {
    AvailabilityStatus.ACTIVE_NOW: 40,
    AvailabilityStatus.STARTS_SOON: 30,
    AvailabilityStatus.ACTIVE_LATER_TODAY: 20,
    AvailabilityStatus.ENDED_TODAY: 5,
    AvailabilityStatus.CURRENTLY_UNAVAILABLE: 0,
}

_FRESH = {
    "fresh": 30,
    "aging": 18,
    "unverified": 8,
    "stale": 0,
    "expired": 0,
    "verification_failed": 0,
}


@dataclass(frozen=True)
class RankedOffer:
    deal: Any
    availability: DealAvailability
    freshness: str
    score: int
    extra_offer_count: int


def freshness_rank_key(status: str | None) -> str:
    return (status or "unverified").casefold()


def is_map_visible_freshness(status: str | None) -> bool:
    return freshness_rank_key(status) not in {"stale", "expired", "verification_failed"}


def offer_score(
    *,
    availability: DealAvailability,
    freshness: str,
    source_confidence: Decimal | None,
    deal_price: Decimal | None,
    percent_savings: Decimal | None,
) -> int:
    score = _AVAIL.get(availability.status, 0) + _FRESH.get(freshness_rank_key(freshness), 0)
    if source_confidence is not None:
        score += int(source_confidence * 10)
    if percent_savings is not None:
        score += min(int(percent_savings), 40)
    elif deal_price is not None and deal_price <= 12:
        score += 8
    return score


def pick_best_offer(
    deals: list[Any],
    availabilities: dict[Any, DealAvailability],
) -> RankedOffer | None:
    ranked: list[RankedOffer] = []
    for deal in deals:
        if not is_map_visible_freshness(getattr(deal, "freshness_status", None)):
            continue
        availability = availabilities.get(deal.id)
        if availability is None:
            continue
        freshness = freshness_rank_key(getattr(deal, "freshness_status", None))
        cheapest = None
        percent = None
        for item in getattr(deal, "items", []) or []:
            if item.deal_price is not None and (cheapest is None or item.deal_price < cheapest):
                cheapest = item.deal_price
            _abs, pct = savings(getattr(item, "normal_price", None), getattr(item, "deal_price", None))
            if pct is not None:
                percent = pct if percent is None else max(percent, pct)
        score = offer_score(
            availability=availability,
            freshness=freshness,
            source_confidence=getattr(deal, "source_confidence", None),
            deal_price=cheapest,
            percent_savings=percent,
        )
        ranked.append(
            RankedOffer(
                deal=deal,
                availability=availability,
                freshness=freshness,
                score=score,
                extra_offer_count=0,
            )
        )
    if not ranked:
        return None
    ranked.sort(key=lambda row: (-row.score, row.deal.title))
    winner = ranked[0]
    return RankedOffer(
        deal=winner.deal,
        availability=winner.availability,
        freshness=winner.freshness,
        score=winner.score,
        extra_offer_count=max(len(ranked) - 1, 0),
    )
