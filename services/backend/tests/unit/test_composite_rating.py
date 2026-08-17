from decimal import Decimal

from app.domain.ratings.composite import ProviderRating, composite_rating


def test_weights_by_review_count() -> None:
    result = composite_rating(
        [
            ProviderRating("google_places", Decimal("4.4"), 890),
            ProviderRating("yelp", Decimal("4.0"), 412),
        ]
    )
    assert result is not None
    assert result.review_count == 1302
    assert result.source_count == 2
    assert result.providers == ("google_places", "yelp")
    # Closer to 4.4 than 4.0 because Google has more reviews, but shrunk slightly toward 3.8.
    assert Decimal("4.2") <= result.score <= Decimal("4.4")


def test_thin_five_star_does_not_outrank_established_four() -> None:
    thin = composite_rating([ProviderRating("yelp", Decimal("5.0"), 3)])
    established = composite_rating([ProviderRating("google_places", Decimal("4.4"), 2000)])
    assert thin is not None and established is not None
    assert thin.score < established.score


def test_empty_sources_return_none() -> None:
    assert composite_rating([]) is None
    assert composite_rating([ProviderRating("yelp", Decimal("4.5"), 0)]) is None
