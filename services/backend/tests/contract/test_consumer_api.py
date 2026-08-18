"""Lock the public consumer API that FindGood.food depends on.

Phase 1 of the platform migration: no schema or route renames. If a later
phase removes or renames a field or filter, these assertions fail on purpose
so the food client is updated in the same change.

Additive keys are allowed. We assert required keys are a subset of the
payload, not that the payload has exactly these keys.
"""

from typing import Any

from app.db.seed import seed
from fastapi.testclient import TestClient

# Fields DealOut must keep returning. Mirrors apps/web/src/lib/api/types.ts Deal.
REQUIRED_DEAL_KEYS = frozenset(
    {
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
)

# Nested venue card on each deal. Food cards link to /venues/{slug}.
REQUIRED_VENUE_CARD_KEYS = frozenset(
    {
        "id",
        "name",
        "slug",
        "primary_category",
        "vertical",
        "neighborhood",
        "city",
        "timezone",
    }
)

# Geography the food app shows and that maps.directionsUrl may consume.
REQUIRED_LOCATION_KEYS = frozenset(
    {
        "id",
        "label",
        "address_line1",
        "address_line2",
        "city",
        "region",
        "postal_code",
        "neighborhood",
        "latitude",
        "longitude",
        "timezone",
    }
)

REQUIRED_ITEM_KEYS = frozenset(
    {
        "id",
        "name",
        "description",
        "category",
        "normal_price",
        "deal_price",
        "currency",
        "absolute_savings",
        "percent_savings",
    }
)

REQUIRED_SCHEDULE_KEYS = frozenset(
    {
        "id",
        "days_of_week",
        "start_time",
        "end_time",
        "ends_at_close",
        "valid_from",
        "valid_until",
    }
)

# Computed in the location timezone. The food UI must not recompute this.
REQUIRED_AVAILABILITY_KEYS = frozenset(
    {
        "status",
        "timezone",
        "local_time",
        "ends_at",
        "next_occurrence",
        "label",
    }
)

REQUIRED_VERIFICATION_KEYS = frozenset(
    {
        "verification_type",
        "verified_at",
        "actor",
        "label",
        "days_ago",
        "is_fresh",
    }
)

# Full venue page: /api/v1/venues/{slug}. List items use the same schema
# with current_deals / upcoming_deals often empty.
REQUIRED_VENUE_KEYS = frozenset(
    {
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
)

REQUIRED_PAGINATION_KEYS = frozenset({"page", "page_size", "total"})

# Query names the food home, city, and neighborhood pages already send.
# food_or_drink is the public alias for offering_kind — do not drop it.
LOCKED_DEAL_FILTERS = frozenset(
    {
        "city",
        "neighborhood",
        "food_or_drink",
        "active_now",
        "deal_type",
    }
)

AVAILABILITY_STATUSES = frozenset(
    {
        "active_now",
        "starts_soon",
        "active_later_today",
        "ended_today",
        "currently_unavailable",
    }
)

OFFERING_KINDS = frozenset({"food", "drink", "both"})

# Evidence bodies stay on admin snapshot routes, not consumer deal JSON.
FORBIDDEN_CONSUMER_DEAL_KEYS = frozenset({"raw_content", "payload", "normalized_payload"})


def _assert_keys(payload: dict[str, Any], required: frozenset[str], label: str) -> None:
    """Fail if a locked field disappeared. Extra keys are fine (additive)."""
    missing = required - set(payload)
    assert not missing, f"{label} missing locked fields: {sorted(missing)}"


def _assert_deal_shape(deal: dict[str, Any]) -> None:
    """Walk one DealOut the way the food DealCard and venue page consume it."""
    _assert_keys(deal, REQUIRED_DEAL_KEYS, "deal")
    assert not (FORBIDDEN_CONSUMER_DEAL_KEYS & set(deal)), "consumer deal leaked snapshot/candidate bodies"
    _assert_keys(deal["venue"], REQUIRED_VENUE_CARD_KEYS, "deal.venue")
    _assert_keys(deal["location"], REQUIRED_LOCATION_KEYS, "deal.location")
    _assert_keys(deal["availability"], REQUIRED_AVAILABILITY_KEYS, "deal.availability")
    _assert_keys(deal["verification"], REQUIRED_VERIFICATION_KEYS, "deal.verification")
    assert deal["availability"]["status"] in AVAILABILITY_STATUSES
    assert deal["offering_kind"] in OFFERING_KINDS
    assert isinstance(deal["vertical"], str) and deal["vertical"]
    assert isinstance(deal["items"], list)
    assert isinstance(deal["schedules"], list)
    for item in deal["items"]:
        _assert_keys(item, REQUIRED_ITEM_KEYS, "deal.item")
    for schedule in deal["schedules"]:
        _assert_keys(schedule, REQUIRED_SCHEDULE_KEYS, "deal.schedule")
        assert schedule["days_of_week"], "schedule must keep at least one ISO weekday"


def test_deal_list_contract_and_locked_filters(client: TestClient) -> None:
    """Home and /los-angeles call GET /api/v1/deals with these filters."""
    seed()

    unfiltered = client.get("/api/v1/deals")
    assert unfiltered.status_code == 200
    body = unfiltered.json()
    _assert_keys(body, frozenset({"items", "pagination"}), "deal list")
    _assert_keys(body["pagination"], REQUIRED_PAGINATION_KEYS, "pagination")
    assert body["pagination"]["total"] >= 1
    assert body["items"], "seed catalog must expose at least one published deal"
    for deal in body["items"]:
        _assert_deal_shape(deal)

    # Detail uses the same DealOut as list items so DealCard and getDeal stay aligned.
    first_id = body["items"][0]["id"]
    detail = client.get(f"/api/v1/deals/{first_id}")
    assert detail.status_code == 200
    _assert_deal_shape(detail.json())

    # City: food home hardcodes Los Angeles. A miss must be empty, not 500.
    la = client.get("/api/v1/deals", params={"city": "Los Angeles"})
    assert la.status_code == 200
    assert la.json()["items"]
    empty_city = client.get("/api/v1/deals", params={"city": "Not A Seeded City"})
    assert empty_city.status_code == 200
    assert empty_city.json()["items"] == []

    # Neighborhood pages pass neighborhood=Downtown (Harbor & Rye).
    downtown = client.get("/api/v1/deals", params={"city": "Los Angeles", "neighborhood": "Downtown"})
    assert downtown.status_code == 200
    downtown_items = downtown.json()["items"]
    assert downtown_items
    assert all(deal["location"]["neighborhood"] == "Downtown" for deal in downtown_items)

    # food_or_drink is the alias the Next query string uses (offering=food|drink).
    food_only = client.get("/api/v1/deals", params={"food_or_drink": "food"})
    assert food_only.status_code == 200
    assert food_only.json()["items"]
    assert all(deal["offering_kind"] in {"food", "both"} for deal in food_only.json()["items"])

    drink_only = client.get("/api/v1/deals", params={"food_or_drink": "drink"})
    assert drink_only.status_code == 200
    assert drink_only.json()["items"]
    assert all(deal["offering_kind"] in {"drink", "both"} for deal in drink_only.json()["items"])

    # deal_type stays a first-class filter even though values are food-centric today.
    happy_hour = client.get("/api/v1/deals", params={"deal_type": "happy_hour"})
    assert happy_hour.status_code == 200
    happy_items = happy_hour.json()["items"]
    assert happy_items
    assert all(deal["deal_type"] == "happy_hour" for deal in happy_items)

    # Happening-now chip sends active_now=1. Domain filter; must not 500.
    active = client.get("/api/v1/deals", params={"active_now": True})
    assert active.status_code == 200
    for deal in active.json()["items"]:
        assert deal["availability"]["status"] == "active_now"

    # Combined query the food FilterBar can produce. 422 means a locked name broke.
    combined = {
        "city": "Los Angeles",
        "neighborhood": "Downtown",
        "food_or_drink": "both",
        "active_now": False,
        "deal_type": "happy_hour",
    }
    assert set(combined) == LOCKED_DEAL_FILTERS
    accepted = client.get("/api/v1/deals", params=combined)
    assert accepted.status_code == 200


def test_deal_list_discovery_filters(client: TestClient) -> None:
    """Homepage search and compact filters are additive query params."""
    seed()

    search = client.get("/api/v1/deals", params={"q": "Harbor"})
    assert search.status_code == 200
    assert search.json()["items"]
    assert all("Harbor" in deal["venue"]["name"] or "Harbor" in deal["title"] for deal in search.json()["items"])

    mexican = client.get("/api/v1/deals", params={"cuisine": "mexican"})
    assert mexican.status_code == 200
    assert mexican.json()["items"]
    assert all(
        "mexican" in deal["venue"].get("cuisines", []) or deal["venue"]["primary_category"] == "mexican"
        for deal in mexican.json()["items"]
    )

    cheap = client.get("/api/v1/deals", params={"price_level": 1})
    assert cheap.status_code == 200
    assert cheap.json()["items"]
    assert all(deal["venue"].get("price_level") == 1 for deal in cheap.json()["items"])

    cocktails = client.get("/api/v1/deals", params={"drink": "cocktails"})
    assert cocktails.status_code == 200
    assert cocktails.json()["items"]
    assert all("cocktails" in deal["venue"].get("drink_kinds", []) for deal in cocktails.json()["items"])

    reserved = client.get("/api/v1/deals", params={"reservations": True})
    assert reserved.status_code == 200
    assert reserved.json()["items"]
    assert all(deal["venue"].get("accepts_reservations") is True for deal in reserved.json()["items"])

    patio = client.get("/api/v1/deals", params={"feature": "patio"})
    assert patio.status_code == 200
    assert patio.json()["items"]
    assert all("patio" in deal["venue"].get("features", []) for deal in patio.json()["items"])

    evening = client.get("/api/v1/deals", params={"when": "evening"})
    assert evening.status_code == 200
    assert evening.json()["items"]

    unknown = client.get("/api/v1/deals", params={"cuisine": "not-a-cuisine"})
    assert unknown.status_code == 422

    stars = client.get("/api/v1/deals", params={"min_rating": "4"})
    assert stars.status_code == 200
    assert stars.json()["items"]
    for deal in stars.json()["items"]:
        rating = deal["venue"].get("rating")
        assert rating is not None
        assert float(rating) >= 4
        providers = {row["provider"] for row in deal["venue"].get("provider_ratings") or []}
        assert "tripadvisor" in providers

    yelp_stars = client.get("/api/v1/deals", params={"min_rating": "4.5", "rating_source": "yelp"})
    assert yelp_stars.status_code == 200
    assert yelp_stars.json()["items"]
    for deal in yelp_stars.json()["items"]:
        yelp = next(row for row in deal["venue"]["provider_ratings"] if row["provider"] == "yelp")
        assert float(yelp["rating"]) >= 4.5

    tripadvisor_stars = client.get("/api/v1/deals", params={"min_rating": "4.5", "rating_source": "tripadvisor"})
    assert tripadvisor_stars.status_code == 200
    assert tripadvisor_stars.json()["items"]
    for deal in tripadvisor_stars.json()["items"]:
        tripadvisor = next(row for row in deal["venue"]["provider_ratings"] if row["provider"] == "tripadvisor")
        assert float(tripadvisor["rating"]) >= 4.5

    ranked = client.get("/api/v1/deals", params={"rating_source": "google_places", "sort": "rating"})
    assert ranked.status_code == 200
    google_scores = [
        float(next(row for row in deal["venue"]["provider_ratings"] if row["provider"] == "google_places")["rating"])
        for deal in ranked.json()["items"]
    ]
    assert google_scores == sorted(google_scores, reverse=True)

    unknown_source = client.get("/api/v1/deals", params={"rating_source": "not-a-source"})
    assert unknown_source.status_code == 422


def test_vertical_filter_defaults_to_food(client: TestClient) -> None:
    """Omitted vertical and vertical=food return seed food deals; beauty is empty."""
    seed()
    omitted = client.get("/api/v1/deals", params={"city": "Los Angeles"})
    explicit = client.get("/api/v1/deals", params={"city": "Los Angeles", "vertical": "food"})
    beauty = client.get("/api/v1/deals", params={"city": "Los Angeles", "vertical": "beauty"})
    invalid = client.get("/api/v1/deals", params={"vertical": "not-a-vertical"})
    assert omitted.status_code == 200
    assert explicit.status_code == 200
    assert omitted.json()["items"]
    assert explicit.json()["items"]
    assert all(deal["vertical"] == "food" for deal in omitted.json()["items"])
    assert all(deal["vertical"] == "food" for deal in explicit.json()["items"])
    assert beauty.status_code == 200
    assert beauty.json()["items"] == []
    assert invalid.status_code == 422

    venues = client.get("/api/v1/venues", params={"city": "Los Angeles"})
    beauty_venues = client.get("/api/v1/venues", params={"city": "Los Angeles", "vertical": "beauty"})
    assert venues.json()["items"]
    assert all(venue["vertical"] == "food" for venue in venues.json()["items"])
    assert beauty_venues.json()["items"] == []


def test_venue_list_and_slug_contract(client: TestClient) -> None:
    """Venue pages use GET /api/v1/venues/{slug}; list is the admin/browse path."""
    seed()

    listed = client.get("/api/v1/venues", params={"city": "Los Angeles"})
    assert listed.status_code == 200
    payload = listed.json()
    _assert_keys(payload, frozenset({"items", "pagination"}), "venue list")
    _assert_keys(payload["pagination"], REQUIRED_PAGINATION_KEYS, "venue pagination")
    assert payload["items"]
    for venue in payload["items"]:
        _assert_keys(venue, REQUIRED_VENUE_KEYS, "venue")
        assert isinstance(venue["locations"], list)
        for location in venue["locations"]:
            _assert_keys(location, REQUIRED_LOCATION_KEYS, "venue.location")

    slug = payload["items"][0]["slug"]
    detail = client.get(f"/api/v1/venues/{slug}")
    assert detail.status_code == 200
    venue = detail.json()
    _assert_keys(venue, REQUIRED_VENUE_KEYS, "venue detail")
    # Detail loads deals so the food venue page can split happening-now vs coming-up.
    for deal in venue["current_deals"] + venue["upcoming_deals"]:
        _assert_deal_shape(deal)

    missing = client.get("/api/v1/venues/not-a-real-slug")
    assert missing.status_code == 404


def test_map_viewport_returns_findgood_pins_without_google_ids(client: TestClient) -> None:
    seed()
    response = client.get(
        "/api/v1/map/locations",
        params={
            "north": "34.20",
            "south": "33.90",
            "east": "-118.10",
            "west": "-118.55",
            "zoom": "12",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    lantern = next((pin for pin in body["items"] if pin["slug"] == "the-lantern-annex"), None)
    assert lantern is not None
    assert lantern["best_offer"]["label"]
    slugs = [pin["slug"] for pin in body["items"]]
    assert slugs.count("the-lantern-annex") == 1
    assert slugs.count("harbor-rye") <= 1
    venue = client.get("/api/v1/venues/the-lantern-annex")
    assert venue.status_code == 200
    providers = {link.get("provider") for link in venue.json().get("provider_ratings") or []}
    assert "google_places" not in providers

    invalid = client.get(
        "/api/v1/map/locations",
        params={"north": "10", "south": "20", "east": "1", "west": "0", "zoom": "12"},
    )
    assert invalid.status_code == 422
