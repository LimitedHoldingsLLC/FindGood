"""Controlled vertical taxonomy. Applications query this; they do not fork catalogs."""

from enum import StrEnum


class Vertical(StrEnum):
    FOOD = "food"
    BEAUTY = "beauty"
    FITNESS = "fitness"
    ENTERTAINMENT = "entertainment"
    ACTIVITIES = "activities"
    RETAIL = "retail"
    SERVICES = "services"
    HEALTH = "health"
    TRAVEL = "travel"
    OTHER = "other"


# FindGood.food is the first app. Consumer list endpoints default here so a
# later beauty row cannot appear on findgood.food just because the client omitted the param.
CONSUMER_DEFAULT_VERTICAL = Vertical.FOOD


def resolve_consumer_vertical(requested: str | None) -> Vertical:
    """Map an optional list filter to the vertical actually queried.

    None means food. Invalid values raise ValueError for the API layer to turn into 422.
    """
    if requested is None or requested == "":
        return CONSUMER_DEFAULT_VERTICAL
    try:
        return Vertical(requested)
    except ValueError as exc:
        raise ValueError(f"Unknown vertical: {requested}") from exc
