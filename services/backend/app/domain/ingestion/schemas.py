"""Normalized records every provider must produce.

Google, Yelp, OpenTable, and the website crawler all speak different languages.
The rest of FindGood only sees these shapes, so adding a fourth provider later
does not require rewriting venues, deals, or the admin UI.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class NormalizedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NormalizedLocation(NormalizedModel):
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


class NormalizedSource(NormalizedModel):
    provider: str
    provider_record_id: str | None = None
    source_url: str | None = None
    retrieved_at: datetime
    confidence: Decimal = Decimal("0.700")
    raw_excerpt: str | None = None


class NormalizedBusiness(NormalizedModel):
    provider: str
    provider_business_id: str
    name: str
    phone: str | None = None
    website_url: str | None = None
    categories: list[str] = Field(default_factory=list)
    location: NormalizedLocation
    google_maps_url: str | None = None
    provider_url: str | None = None
    rating: Decimal | None = None
    review_count: int | None = None
    opening_hours: dict | None = None
    retrieved_at: datetime
    extra: dict = Field(default_factory=dict)


class NormalizedOfferSchedule(NormalizedModel):
    days_of_week: list[int] = Field(default_factory=list)
    start_time: str | None = None
    end_time: str | None = None
    ends_at_close: bool = False
    start_date: date | None = None
    end_date: date | None = None


class NormalizedOfferItem(NormalizedModel):
    name: str
    description: str | None = None
    category: str | None = None
    original_price: Decimal | None = None
    offer_price: Decimal | None = None
    currency: str = "USD"


class NormalizedOffer(NormalizedModel):
    title: str
    description: str | None = None
    deal_type: str = "other"
    offering_kind: str = "both"
    schedules: list[NormalizedOfferSchedule] = Field(default_factory=list)
    items: list[NormalizedOfferItem] = Field(default_factory=list)
    source: NormalizedSource
    raw_text: str | None = None
    confidence: Decimal = Decimal("0.500")
    extraction_method: str = "heuristic"
    observed_at: datetime
