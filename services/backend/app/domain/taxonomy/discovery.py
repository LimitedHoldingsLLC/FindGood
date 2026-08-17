"""Consumer discovery facets. Controlled values — not free-text tags from crawlers."""

from enum import StrEnum


class Cuisine(StrEnum):
    AMERICAN = "american"
    MEXICAN = "mexican"
    JAPANESE = "japanese"
    KOREAN = "korean"
    CHINESE = "chinese"
    THAI = "thai"
    VIETNAMESE = "vietnamese"
    ITALIAN = "italian"
    FRENCH = "french"
    MEDITERRANEAN = "mediterranean"
    INDIAN = "indian"
    SEAFOOD = "seafood"
    CAFE = "cafe"
    BAR = "bar"
    GASTROPUB = "gastropub"


class DrinkKind(StrEnum):
    COCKTAILS = "cocktails"
    BEER = "beer"
    WINE = "wine"
    NATURAL_WINE = "natural_wine"
    SAKE = "sake"
    NONALCOHOLIC = "nonalcoholic"


class VenueFeature(StrEnum):
    PATIO = "patio"
    ROOFTOP = "rooftop"
    OUTDOOR = "outdoor"
    LATE_NIGHT = "late_night"
    GOOD_FOR_GROUPS = "good_for_groups"
    WALK_IN = "walk_in"


class TimeBucket(StrEnum):
    LUNCH = "lunch"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    LATE_NIGHT = "late_night"


PRICE_LEVELS = frozenset({1, 2, 3, 4})
ISO_WEEKDAYS = frozenset(range(1, 8))
