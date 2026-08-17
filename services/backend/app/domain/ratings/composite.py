"""FindGood.Food composite rating. No FastAPI, no provider HTTP.

Each official provider gives a star score and a review count. We do not treat a
5.0 from three reviews as better than a 4.4 from two thousand. The score shrinks
toward a prior so thin evidence cannot dominate the filter.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

PRIOR_MEAN = Decimal("3.80")
PRIOR_WEIGHT = 40
QUANTUM = Decimal("0.1")
FIVE = Decimal("5")


@dataclass(frozen=True)
class ProviderRating:
    provider: str
    rating: Decimal
    review_count: int
    scale: int = 5


@dataclass(frozen=True)
class CompositeRating:
    score: Decimal
    review_count: int
    source_count: int
    providers: tuple[str, ...]


def composite_rating(
    sources: list[ProviderRating],
    *,
    prior: Decimal = PRIOR_MEAN,
    prior_weight: int = PRIOR_WEIGHT,
) -> CompositeRating | None:
    usable = [source for source in sources if source.review_count > 0 and source.rating is not None]
    if not usable:
        return None
    weighted = Decimal("0")
    total = 0
    for source in usable:
        stars = _on_five(source.rating, source.scale)
        weighted += stars * source.review_count
        total += source.review_count
    score = (prior * prior_weight + weighted) / (prior_weight + total)
    providers = tuple(sorted({source.provider for source in usable}))
    return CompositeRating(
        score=score.quantize(QUANTUM),
        review_count=total,
        source_count=len(providers),
        providers=providers,
    )


def apply_to_venue(venue: object, sources: list[ProviderRating]) -> CompositeRating | None:
    """Write composite columns onto a venue-like object."""
    result = composite_rating(sources)
    if result is None:
        venue.rating = None
        venue.rating_review_count = 0
        venue.rating_source_count = 0
        venue.rating_providers = []
        return None
    venue.rating = result.score
    venue.rating_review_count = result.review_count
    venue.rating_source_count = result.source_count
    venue.rating_providers = list(result.providers)
    return result


def ratings_from_links(links: list[Any]) -> list[ProviderRating]:
    """Read structured link columns, then extra_metadata for older rows."""
    out: list[ProviderRating] = []
    for link in links:
        rating = link.rating
        count = link.review_count
        if rating is None:
            meta = link.extra_metadata or {}
            raw = meta.get("rating")
            if raw is not None:
                rating = Decimal(str(raw))
                count = int(meta.get("review_count") or 0)
        if rating is None or not count:
            continue
        out.append(
            ProviderRating(
                provider=str(link.provider),
                rating=Decimal(str(rating)),
                review_count=int(count),
            )
        )
    return out


def _on_five(rating: Decimal, scale: int) -> Decimal:
    if scale == 5:
        return rating
    if scale <= 0:
        return rating
    return (rating * FIVE / Decimal(scale)).quantize(Decimal("0.01"))
