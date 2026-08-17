from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Pagination(APIModel):
    page: int
    page_size: int
    total: int


class ScoreFactorOut(APIModel):
    name: str
    contribution: float
    explanation: str


class DealScoreOut(APIModel):
    score: int
    factors: list[ScoreFactorOut]


class AvailabilityOut(APIModel):
    status: str
    timezone: str
    local_time: datetime
    ends_at: datetime | None
    next_occurrence: datetime | None
    label: str


class VerificationOut(APIModel):
    verification_type: str
    verified_at: datetime | None
    actor: str | None
    label: str
    days_ago: int | None
    is_fresh: bool


class ProvenanceOut(APIModel):
    source_type: str | None = None
    source_url: str | None = None
    snapshot_id: UUID | None = None
    published_by: str | None = None
    published_at: datetime | None = None


class DealItemOut(APIModel):
    id: UUID
    name: str
    description: str | None
    category: str | None
    normal_price: Decimal | None
    deal_price: Decimal | None
    currency: str
    absolute_savings: Decimal | None
    percent_savings: Decimal | None


class DealScheduleOut(APIModel):
    id: UUID
    days_of_week: list[int]
    start_time: time | None
    end_time: time | None
    ends_at_close: bool
    valid_from: date | None
    valid_until: date | None


class VenueCardOut(APIModel):
    id: UUID
    name: str
    slug: str
    primary_category: str
    vertical: str
    neighborhood: str | None
    city: str
    timezone: str


class DealOut(APIModel):
    id: UUID
    title: str
    description: str | None
    deal_type: str
    offering_kind: str
    vertical: str
    source_confidence: Decimal
    venue: VenueCardOut
    location: "LocationOut"
    items: list[DealItemOut]
    schedules: list[DealScheduleOut]
    availability: AvailabilityOut
    verification: VerificationOut
    provenance: ProvenanceOut | None = None
    score: DealScoreOut | None = None
    distance_km: float | None = None
    freshness_status: str | None = None
    last_seen_at: datetime | None = None
    last_verified_at: datetime | None = None


class LocationOut(APIModel):
    id: UUID
    label: str
    address_line1: str
    address_line2: str | None
    city: str
    region: str
    postal_code: str
    neighborhood: str | None
    latitude: Decimal
    longitude: Decimal
    timezone: str


class VenueOut(APIModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    website_url: str | None
    phone: str | None
    primary_category: str
    vertical: str
    status: str
    locations: list[LocationOut]
    current_deals: list[DealOut] = Field(default_factory=list)
    upcoming_deals: list[DealOut] = Field(default_factory=list)


class DealListOut(APIModel):
    items: list[DealOut]
    pagination: Pagination


class VenueListOut(APIModel):
    items: list[VenueOut]
    pagination: Pagination


class HealthOut(APIModel):
    status: str
    service: str


class ReadyOut(APIModel):
    status: str
    database: bool
    queue: bool


class FeatureFlagsOut(APIModel):
    flags: dict[str, bool]


class VenueCreateIn(APIModel):
    name: str
    description: str | None = None
    website_url: str | None = None
    phone: str | None = None
    primary_category: str = "restaurant"
    vertical: str = "food"
    status: str = "published"


class VenueUpdateIn(APIModel):
    name: str | None = None
    description: str | None = None
    website_url: str | None = None
    phone: str | None = None
    primary_category: str | None = None
    vertical: str | None = None
    status: str | None = None


class LocationCreateIn(APIModel):
    label: str = "Main"
    address_line1: str
    address_line2: str | None = None
    city: str
    region: str
    postal_code: str
    country: str = "US"
    neighborhood: str | None = None
    latitude: Decimal
    longitude: Decimal
    timezone: str = "America/Los_Angeles"
    status: str = "published"


class ScheduleCreateIn(APIModel):
    days_of_week: list[int]
    start_time: time | None = None
    end_time: time | None = None
    ends_at_close: bool = False
    valid_from: date | None = None
    valid_until: date | None = None


class ItemCreateIn(APIModel):
    name: str
    description: str | None = None
    category: str | None = None
    normal_price: Decimal | None = None
    deal_price: Decimal | None = None
    currency: str = "USD"


class DealCreateIn(APIModel):
    venue_location_id: UUID
    title: str
    description: str | None = None
    deal_type: str = "other"
    offering_kind: str = "both"
    vertical: str = "food"
    status: str = "published"
    publication_state: str = "published"
    source_confidence: Decimal = Decimal("1.000")
    schedules: list[ScheduleCreateIn] = Field(default_factory=list)
    items: list[ItemCreateIn] = Field(default_factory=list)


class DealUpdateIn(APIModel):
    title: str | None = None
    description: str | None = None
    deal_type: str | None = None
    offering_kind: str | None = None
    vertical: str | None = None
    status: str | None = None
    publication_state: str | None = None


class SourceCreateIn(APIModel):
    venue_id: UUID | None = None
    source_type: str = "demo"
    url: str
    canonical_identity: str | None = None
    crawl_enabled: bool = True
    crawl_frequency_minutes: int = 1440
    trust_level: str = "medium"


class SourceOut(APIModel):
    id: UUID
    venue_id: UUID | None
    source_type: str
    url: str
    canonical_identity: str
    is_active: bool
    crawl_enabled: bool
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_error: str | None
    trust_level: str


class SnapshotOut(APIModel):
    id: UUID
    source_id: UUID
    crawl_run_id: UUID | None
    fetched_at: datetime
    http_status: int | None
    content_type: str | None
    content_hash: str
    storage_ref: str | None
    parser_version: str | None
    extra_metadata: dict
    raw_content: str | None = None


class CandidateOut(APIModel):
    id: UUID
    source_snapshot_id: UUID
    crawl_run_id: UUID | None
    candidate_type: str
    payload: dict
    normalized_payload: dict
    validation_status: str
    validation_errors: list
    review_status: str
    published_deal_id: UUID | None
    confidence: Decimal
    diagnostic_notes: str | None


class CrawlRunOut(APIModel):
    id: UUID
    source_id: UUID
    started_at: datetime
    completed_at: datetime | None
    status: str
    fetch_result: str | None
    parse_result: str | None
    extracted_count: int
    error_category: str | None
    error_details: str | None
    retry_count: int


class VerifyIn(APIModel):
    verification_type: str = "manual"
    notes: str | None = None
    actor: str = "admin"


class AdminSessionIn(APIModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class AdminSessionOut(APIModel):
    ok: bool
    subject: str
    token: str
    expires_at: datetime


class JobAcceptedOut(APIModel):
    job_id: str
    source_id: UUID


DealOut.model_rebuild()
VenueOut.model_rebuild()
