from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.db.models.enums import FreshnessStatus, SightingState
from app.domain.duplicates.matcher import SimpleDuplicateMatcher, VenueIdentity, classify_match
from app.domain.verification.policy import evaluate_freshness


def _venue(**kwargs) -> VenueIdentity:
    defaults = dict(
        id="x",
        name="Harbor & Rye",
        city="Los Angeles",
        phone=None,
        website_url=None,
        latitude=None,
        longitude=None,
    )
    defaults.update(kwargs)
    return VenueIdentity(**defaults)


def test_same_phone_is_a_match() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        _venue(id="new", phone="213-555-0142"),
        [_venue(id="old", name="Other Name", phone="2135550142")],
    )
    assert matches[0].entity_id == "old"
    assert "phone" in matches[0].reasons


def test_same_domain_is_a_match() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        _venue(id="new", name="Place A", website_url="https://harborandrye.com/menu"),
        [_venue(id="old", name="Place B", website_url="https://www.harborandrye.com")],
    )
    assert matches[0].entity_id == "old"
    assert "website" in matches[0].reasons


def test_same_name_different_cities_are_not_merged() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        _venue(id="la", city="Los Angeles"),
        [_venue(id="nyc", city="New York")],
    )
    assert matches == []
    assert classify_match(None) == "new"


def test_nearby_same_name_is_handled() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        _venue(id="new", latitude=Decimal("34.090000"), longitude=Decimal("-118.280000")),
        [_venue(id="old", latitude=Decimal("34.090100"), longitude=Decimal("-118.280100"))],
    )
    assert matches
    assert "nearby_same_name" in matches[0].reasons
    # Name+city plus nearby is review or auto depending on score; never ignored.
    assert classify_match(matches[0]) in {"auto_merge", "review"}


def test_name_and_city_alone_does_not_auto_merge() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        _venue(id="new"),
        [_venue(id="old")],
    )
    assert matches
    assert classify_match(matches[0]) == "review"


def test_explicit_end_date_expires() -> None:
    now = datetime(2026, 8, 16, tzinfo=UTC)
    result = evaluate_freshness(
        kind="happy_hour",
        now=now,
        last_verified_at=now,
        explicit_end_date=(now.date() - timedelta(days=1)),
    )
    assert result.status == FreshnessStatus.EXPIRED


def test_failed_fetch_is_not_disappearance() -> None:
    now = datetime(2026, 8, 16, tzinfo=UTC)
    result = evaluate_freshness(
        kind="happy_hour",
        now=now,
        last_verified_at=now - timedelta(days=1),
        verification_failed=True,
    )
    assert result.status == FreshnessStatus.VERIFICATION_FAILED


def test_never_verified_is_unverified() -> None:
    now = datetime(2026, 8, 16, tzinfo=UTC)
    result = evaluate_freshness(kind="venue_identity", now=now, last_verified_at=None)
    assert result.status == FreshnessStatus.UNVERIFIED


def test_removed_sighting_is_not_fresh() -> None:
    now = datetime(2026, 8, 16, tzinfo=UTC)
    result = evaluate_freshness(
        kind="happy_hour",
        now=now,
        last_verified_at=now,
        sighting_state=SightingState.REMOVED,
    )
    assert result.status == FreshnessStatus.STALE
