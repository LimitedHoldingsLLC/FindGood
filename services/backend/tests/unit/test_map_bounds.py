from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.domain.map.bounds import InvalidBounds, parse_bounds
from app.domain.map.cache_key import encode, precision_for_zoom
from app.domain.map.labels import marker_label
from app.domain.map.ranking import is_map_visible_freshness, offer_score, pick_best_offer
from app.domain.schedules.engine import AvailabilityStatus, DealAvailability


def test_rejects_inverted_and_out_of_range_bounds() -> None:
    with pytest.raises(InvalidBounds):
        parse_bounds(north=Decimal("10"), south=Decimal("20"), east=Decimal("1"), west=Decimal("0"))
    with pytest.raises(InvalidBounds):
        parse_bounds(north=Decimal("91"), south=Decimal("10"), east=Decimal("1"), west=Decimal("0"))


def test_antimeridian_contains_both_sides() -> None:
    bounds = parse_bounds(north=Decimal("10"), south=Decimal("-10"), east=Decimal("-170"), west=Decimal("170"))
    assert bounds.crosses_antimeridian
    assert bounds.contains(Decimal("0"), Decimal("175"))
    assert bounds.contains(Decimal("0"), Decimal("-175"))
    assert not bounds.contains(Decimal("0"), Decimal("0"))


def test_stale_and_expired_offers_are_hidden() -> None:
    assert is_map_visible_freshness("fresh")
    assert is_map_visible_freshness("aging")
    assert not is_map_visible_freshness("stale")
    assert not is_map_visible_freshness("expired")


def test_active_fresh_deal_outranks_later_aging_deal() -> None:
    now = datetime(2026, 8, 17, 20, 0)
    active = DealAvailability(AvailabilityStatus.ACTIVE_NOW, "America/Los_Angeles", now, None, now, "Now")
    later = DealAvailability(AvailabilityStatus.ACTIVE_LATER_TODAY, "America/Los_Angeles", now, None, now, "Later")
    winning = offer_score(
        availability=active, freshness="fresh", source_confidence=None, deal_price=None, percent_savings=None
    )
    losing = offer_score(
        availability=later, freshness="aging", source_confidence=None, deal_price=None, percent_savings=None
    )
    assert winning > losing


def test_marker_label_prefers_price() -> None:
    class Item:
        deal_price = Decimal("6.00")
        name = "Martini"

    assert marker_label(title="Annex hour", deal_type="happy_hour", items=[Item()]) == "$6 HH"


def test_pick_best_offer_hides_stale_and_returns_one_winner() -> None:
    now = datetime(2026, 8, 17, 20, 0)
    active = DealAvailability(AvailabilityStatus.ACTIVE_NOW, "America/Los_Angeles", now, None, now, "Now")
    later = DealAvailability(AvailabilityStatus.ACTIVE_LATER_TODAY, "America/Los_Angeles", now, None, now, "Later")
    stale = SimpleNamespace(id="stale", title="Old hour", freshness_status="stale", items=[], source_confidence=None)
    fresh = SimpleNamespace(id="fresh", title="Martini", freshness_status="fresh", items=[], source_confidence=None)
    aging = SimpleNamespace(id="aging", title="Beer", freshness_status="aging", items=[], source_confidence=None)
    winner = pick_best_offer(
        [stale, fresh, aging],
        {"stale": active, "fresh": active, "aging": later},
    )
    assert winner is not None
    assert winner.deal.id == "fresh"
    assert winner.extra_offer_count == 1
    assert pick_best_offer([stale], {"stale": active}) is None


def test_geohash_is_stable() -> None:
    assert encode(34.05, -118.24, precision=5) == encode(34.05, -118.24, precision=5)
    assert precision_for_zoom(16) == 6
