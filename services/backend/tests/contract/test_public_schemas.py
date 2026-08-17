"""Lock Pydantic consumer schemas without needing Postgres.

HTTP contract tests cover live JSON. This module fails in unit CI if someone
renames a DealOut / VenueOut field before the food TypeScript client is updated.
"""

import inspect

from app.api.routes.deals import list_deals
from app.api.schemas import (
    AvailabilityOut,
    DealItemOut,
    DealListOut,
    DealOut,
    DealScheduleOut,
    LocationOut,
    Pagination,
    VenueCardOut,
    VenueListOut,
    VenueOut,
    VerificationOut,
)

# Must stay in sync with test_consumer_api.REQUIRED_* and apps/web types.
DEAL_FIELDS = {
    "id",
    "title",
    "description",
    "deal_type",
    "offering_kind",
    "vertical",
    "source_confidence",
    "venue",
    "location",
    "items",
    "schedules",
    "availability",
    "verification",
    "provenance",
    "score",
    "distance_km",
}
VENUE_FIELDS = {
    "id",
    "name",
    "slug",
    "description",
    "website_url",
    "phone",
    "primary_category",
    "vertical",
    "status",
    "locations",
    "current_deals",
    "upcoming_deals",
}


def test_deal_and_venue_schema_fields_remain() -> None:
    """Required model fields are a subset of the schema (additive extras OK)."""
    assert DEAL_FIELDS <= set(DealOut.model_fields)
    assert VENUE_FIELDS <= set(VenueOut.model_fields)
    assert {"items", "pagination"} <= set(DealListOut.model_fields)
    assert {"items", "pagination"} <= set(VenueListOut.model_fields)
    assert {"page", "page_size", "total"} <= set(Pagination.model_fields)
    assert {"id", "name", "slug", "primary_category", "vertical", "neighborhood", "city", "timezone"} <= set(
        VenueCardOut.model_fields
    )
    assert {
        "id",
        "label",
        "address_line1",
        "city",
        "region",
        "postal_code",
        "latitude",
        "longitude",
        "timezone",
    } <= set(LocationOut.model_fields)
    assert {"status", "timezone", "local_time", "ends_at", "next_occurrence", "label"} <= set(
        AvailabilityOut.model_fields
    )
    assert {"verification_type", "verified_at", "actor", "label", "days_ago", "is_fresh"} <= set(
        VerificationOut.model_fields
    )
    assert {"normal_price", "deal_price", "absolute_savings", "percent_savings", "currency"} <= set(
        DealItemOut.model_fields
    )
    assert {"days_of_week", "start_time", "end_time", "ends_at_close"} <= set(DealScheduleOut.model_fields)


def test_deal_list_keeps_food_or_drink_alias() -> None:
    """apps/web sends food_or_drink, not offering_kind, on the query string."""
    offering = inspect.signature(list_deals).parameters["offering_kind"]
    query = offering.default
    assert query.alias == "food_or_drink"


def test_deal_list_accepts_vertical_query() -> None:
    assert "vertical" in inspect.signature(list_deals).parameters


def test_deal_list_accepts_discovery_filters() -> None:
    params = inspect.signature(list_deals).parameters
    for name in ("q", "cuisine", "price_level", "drink", "reservations", "feature", "when", "day", "min_rating"):
        assert name in params
