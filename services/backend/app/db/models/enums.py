from enum import StrEnum


class RecordStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DISABLED = "disabled"


class PublicationState(StrEnum):
    UNPUBLISHED = "unpublished"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"


class DealType(StrEnum):
    HAPPY_HOUR = "happy_hour"
    FOOD_SPECIAL = "food_special"
    DRINK_SPECIAL = "drink_special"
    PRIX_FIXE = "prix_fixe"
    OYSTER = "oyster"
    TACO_NIGHT = "taco_night"
    BRUNCH = "brunch"
    LUNCH = "lunch"
    LATE_NIGHT = "late_night"
    LIMITED_TIME = "limited_time"
    OTHER = "other"


class DealOfferingKind(StrEnum):
    FOOD = "food"
    DRINK = "drink"
    BOTH = "both"


class SourceType(StrEnum):
    DEMO = "demo"
    MANUAL = "manual"
    RESTAURANT_WEBSITE = "restaurant_website"
    RESTAURANT_HTML_MENU = "restaurant_html_menu"
    RESTAURANT_PDF = "restaurant_pdf"
    RESTAURANT_SUBMITTED = "restaurant_submitted"
    INSTAGRAM = "instagram"
    THIRD_PARTY = "third_party"


class TrustLevel(StrEnum):
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    INTERNAL = "internal"


class VerificationType(StrEnum):
    MANUAL = "manual"
    RESTAURANT = "restaurant"
    AUTOMATED_SOURCE = "automated_source"
    COMMUNITY = "community"


class CandidateType(StrEnum):
    VENUE = "venue"
    DEAL = "deal"
    SCHEDULE = "schedule"
    ITEM = "item"


class CandidateValidationStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class CandidateReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CrawlRunStatus(StrEnum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"
