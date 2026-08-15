from app.domain.duplicates.matcher import SimpleDuplicateMatcher, VenueIdentity


def test_matches_normalized_name_and_city() -> None:
    matcher = SimpleDuplicateMatcher()
    matches = matcher.match_venues(
        VenueIdentity("new", "Harbor & Rye", "Los Angeles", "213-555-0142", None, None, None),
        [
            VenueIdentity("old", "harbor & rye", "los angeles", None, None, None, None),
            VenueIdentity("other", "Casa Nube", "Los Angeles", None, None, None, None),
        ],
    )
    assert matches[0].entity_id == "old"
    assert "normalized_name_and_city" in matches[0].reasons
