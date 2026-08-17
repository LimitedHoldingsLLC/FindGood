"""Admin/ops API shapes. Separate from the public consumer contract."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpsModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageOut(OpsModel):
    items: list[Any]
    page: int
    page_size: int
    total: int


class OpsOverviewOut(OpsModel):
    system_working: bool
    freshness_health_percent: float
    total_businesses: int
    active_businesses: int
    businesses_added_24h: int
    businesses_added_7d: int
    total_active_offers: int
    offers_added_24h: int
    offers_added_7d: int
    verified_offers: int
    stale_offers: int
    expired_offers: int
    unverified_offers: int
    aging_offers: int
    businesses_needing_refresh: int
    pending_review_items: int
    runs_completed_24h: int
    runs_failed_24h: int
    crawl_failures_24h: int
    provider_failures_24h: int
    businesses_fresh_percent: float
    offers_fresh_percent: float
    freshness_note: str


class OpsDealOut(OpsModel):
    id: UUID
    title: str
    description: str | None
    deal_type: str
    publication_state: str
    freshness_status: str
    sighting_state: str
    extraction_method: str | None
    source_confidence: Decimal
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    last_verified_at: datetime | None
    next_refresh_at: datetime | None
    consecutive_misses: int
    raw_source_text: str | None
    venue_id: UUID | None
    venue_name: str | None
    source_id: UUID | None
    snapshot_id: UUID | None


class OpsVenueOut(OpsModel):
    id: UUID
    name: str
    slug: str
    status: str
    website_url: str | None
    phone: str | None
    city: str | None
    address: str | None
    freshness_status: str
    last_verified_at: datetime | None
    last_seen_at: datetime | None
    next_refresh_at: datetime | None
    failure_count: int
    provider_links: list[dict[str, Any]]
    location_id: UUID | None
    timezone: str | None
    offers: list[OpsDealOut] = Field(default_factory=list)


class IngestionRunOut(OpsModel):
    id: UUID
    provider: str
    job_type: str
    status: str
    requested_by: str
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    target_url: str | None
    venue_id: UUID | None
    source_id: UUID | None
    records_discovered: int
    records_created: int
    records_updated: int
    records_skipped: int
    pages_discovered: int
    pages_fetched: int
    pages_skipped: int
    robots_blocked: int
    offers_discovered: int
    offers_created: int
    offers_updated: int
    retry_count: int
    error_category: str | None
    error_details: str | None
    errors: list[Any]
    extra_metadata: dict[str, Any]
    cancel_requested: bool


class ProviderOut(OpsModel):
    name: str
    configured: bool
    enabled: bool
    key_configured: bool
    last_status: str | None
    last_finished_at: datetime | None
    calls_today: int
    errors_today: int
    rate_limits_today: int
    records_imported_today: int
    note: str | None = None


class ReviewOut(OpsModel):
    id: UUID
    subject_type: str
    subject_id: UUID | None
    reason: str
    status: str
    title: str
    explanation: str
    suggested_action: str | None
    evidence: dict[str, Any]
    created_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None


class ErrorGroupOut(OpsModel):
    category: str
    provider: str | None
    count: int
    first_at: datetime
    latest_at: datetime
    example: str | None


class SystemHealthOut(OpsModel):
    api: str
    postgres: str
    redis: str
    worker: str
    crawler: str
    google: str
    yelp: str
    opentable: str


class SearchOut(OpsModel):
    venues: list[OpsVenueOut]
    deals: list[OpsDealOut]
    runs: list[IngestionRunOut]


class AuditOut(OpsModel):
    id: UUID
    actor: str
    action: str
    target_type: str
    target_id: UUID | None
    metadata_json: dict[str, Any] = Field(validation_alias="metadata_json")
    created_at: datetime


class FreshnessBucketOut(OpsModel):
    buckets: dict[str, int]
    items: list[OpsDealOut]
    page: int
    page_size: int
    total: int


class CrawlIn(OpsModel):
    url: str | None = None
    venue_id: UUID | None = None
    sync: bool = False


class ProviderSearchIn(OpsModel):
    text: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    sync: bool = False


class ReviewActionIn(OpsModel):
    action: str


class BulkVenuesIn(OpsModel):
    venue_ids: list[UUID]
    confirm: bool = False


class NotesIn(OpsModel):
    notes: str | None = None


class CrawlDomainOut(OpsModel):
    host: str
    last_attempt_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    last_http_status: int | None
    success_count: int
    failure_count: int
    consecutive_failures: int
    robots_status: str | None
    avg_response_ms: float | None
    next_permitted_at: datetime | None
    last_error: str | None
