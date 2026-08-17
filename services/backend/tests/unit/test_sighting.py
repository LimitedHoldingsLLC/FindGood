from app.db.models.enums import FreshnessStatus, PublicationState, SightingState
from app.domain.verification.policy import consumer_may_show
from app.domain.verification.sighting import next_sighting_after_miss, offer_appears_on_page


def test_offer_is_present_when_title_is_on_the_page() -> None:
    assert offer_appears_on_page(
        title="Weekday Happy Hour",
        raw_source_text=None,
        page_text="Join us for Weekday Happy Hour from 4 to 6.",
    )


def test_offer_is_absent_when_text_disappeared() -> None:
    assert not offer_appears_on_page(
        title="Weekday Happy Hour",
        raw_source_text="Cocktails $8 4pm-6pm",
        page_text="Our dinner menu is served nightly.",
    )


def test_short_titles_are_not_treated_as_proof() -> None:
    assert not offer_appears_on_page(title="Menu", raw_source_text=None, page_text="Menu hours about contact")


def test_miss_progression_does_not_delete_on_first_miss() -> None:
    assert next_sighting_after_miss(1) == SightingState.NOT_SEEN_ONCE
    assert next_sighting_after_miss(2) == SightingState.VERIFICATION_NEEDED
    assert next_sighting_after_miss(3) == SightingState.REMOVED


def test_consumer_hides_expired_and_stale() -> None:
    assert consumer_may_show(
        freshness_status=FreshnessStatus.FRESH,
        publication_state=PublicationState.PUBLISHED,
        sighting_state=SightingState.ACTIVE,
    )
    assert not consumer_may_show(
        freshness_status=FreshnessStatus.STALE,
        publication_state=PublicationState.PUBLISHED,
        sighting_state=SightingState.ACTIVE,
    )
    assert not consumer_may_show(
        freshness_status=FreshnessStatus.FRESH,
        publication_state=PublicationState.PUBLISHED,
        sighting_state=SightingState.REMOVED,
    )
