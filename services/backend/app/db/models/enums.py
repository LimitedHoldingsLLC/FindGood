from enum import StrEnum

from app.domain.taxonomy.verticals import Vertical

# Re-export so seed, admin, and models can import taxonomy next to DealType.
__all__ = [
    "CandidateReviewStatus",
    "CandidateType",
    "CandidateValidationStatus",
    "CrawlRunStatus",
    "DealOfferingKind",
    "ExtractionMethod",
    "FreshnessStatus",
    "IngestionJobType",
    "IngestionRunStatus",
    "LocationConfidence",
    "ProviderName",
    "ReviewItemStatus",
    "ReviewReason",
    "SightingState",
    "DealType",
    "PublicationState",
    "RecordStatus",
    "SourceType",
    "TrustLevel",
    "VerificationType",
    "Vertical",
]


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
    PERCENTAGE_OFF = "percentage_off"
    FIXED_PRICE = "fixed_price"
    BOGO = "bogo"
    INTRODUCTORY = "introductory"
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
    OFFICIAL_WEBSITE = "official_website"
    OFFICIAL_MENU = "official_menu"
    MERCHANT_SUBMISSION = "merchant_submission"
    PARTNER_API = "partner_api"
    GOOGLE_PLACES = "google_places"
    YELP = "yelp"
    TRIPADVISOR = "tripadvisor"
    OPENTABLE = "opentable"
    USER_REPORT = "user_report"
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
    QUEUED = "queued"
    CANCELLED = "cancelled"


class ProviderName(StrEnum):
    GOOGLE_PLACES = "google_places"
    YELP = "yelp"
    TRIPADVISOR = "tripadvisor"
    OPENTABLE = "opentable"
    WEBSITE_CRAWLER = "website_crawler"
    MANUAL = "manual"
    DEMO = "demo"


class LocationConfidence(StrEnum):
    VERIFIED = "verified"
    HIGH_CONFIDENCE = "high_confidence"
    APPROXIMATE = "approximate"
    NEEDS_REVIEW = "needs_review"
    INVALID = "invalid"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"
    EXPIRED = "expired"
    UNVERIFIED = "unverified"
    VERIFICATION_FAILED = "verification_failed"


class SightingState(StrEnum):
    ACTIVE = "active"
    NOT_SEEN_ONCE = "not_seen_once"
    VERIFICATION_NEEDED = "verification_needed"
    STALE = "stale"
    EXPIRED = "expired"
    REMOVED = "removed"


class IngestionJobType(StrEnum):
    SOURCE_REFRESH = "source_refresh"
    WEBSITE_CRAWL = "website_crawl"
    PROVIDER_SEARCH = "provider_search"
    PROVIDER_REFRESH = "provider_refresh"
    BUSINESS_DISCOVERY = "business_discovery"
    BUSINESS_ENRICHMENT = "business_enrichment"
    OFFER_REFRESH = "offer_refresh"
    STALE_REFRESH = "stale_refresh"
    EXPIRE_PROMOTIONS = "expire_promotions"
    DETECT_STALE = "detect_stale"
    RETRY_FAILED = "retry_failed"


class IngestionRunStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewItemStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"
    MERGED = "merged"
    RECHECK = "recheck"


class ReviewReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    POSSIBLE_DUPLICATE_VENUE = "possible_duplicate_venue"
    POSSIBLE_DUPLICATE_OFFER = "possible_duplicate_offer"
    CONFLICTING_ADDRESS = "conflicting_address"
    CONFLICTING_HOURS = "conflicting_hours"
    UNPARSED_SCHEDULE = "unparsed_schedule"
    STALE_OFFER = "stale_offer"
    SOURCE_DISAPPEARED = "source_disappeared"
    UNEXPECTED_REDIRECT = "unexpected_redirect"
    PROVIDER_WEBSITE_DISAGREE = "provider_website_disagree"
    CRAWL_REPEATED_FAILURE = "crawl_repeated_failure"
    MANUAL = "manual"


class ExtractionMethod(StrEnum):
    STRUCTURED_DATA = "structured_data"
    HEURISTIC = "heuristic"
    DETERMINISTIC = "deterministic"
    MANUAL = "manual"
    PROVIDER_API = "provider_api"
    AI = "ai"
