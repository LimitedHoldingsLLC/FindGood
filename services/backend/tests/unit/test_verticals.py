"""Consumer list default: omitted vertical means food, so FindGood.food stays food-only."""

import pytest
from app.domain.taxonomy.verticals import (
    CONSUMER_DEFAULT_VERTICAL,
    Vertical,
    resolve_consumer_vertical,
)


def test_omitted_vertical_is_food() -> None:
    assert resolve_consumer_vertical(None) == Vertical.FOOD
    assert resolve_consumer_vertical("") == Vertical.FOOD
    assert CONSUMER_DEFAULT_VERTICAL == Vertical.FOOD


def test_explicit_verticals_round_trip() -> None:
    assert resolve_consumer_vertical("food") == Vertical.FOOD
    assert resolve_consumer_vertical("beauty") == Vertical.BEAUTY


def test_unknown_vertical_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown vertical"):
        resolve_consumer_vertical("not-a-vertical")
