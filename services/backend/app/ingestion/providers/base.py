"""Provider adapter contract.

Each external data source (Google Places, Yelp, OpenTable, a restaurant
website) lives in its own module and implements this interface. The rest of
FindGood never talks to those APIs directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.exceptions import ProviderNotConfigured
from app.domain.ingestion.schemas import NormalizedBusiness, NormalizedOffer


@dataclass(frozen=True)
class ProviderSearchQuery:
    text: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: int = 2000
    max_results: int = 20


class ProviderAdapter(Protocol):
    name: str

    def configured(self) -> bool: ...

    def search_businesses(self, query: ProviderSearchQuery) -> list[NormalizedBusiness]: ...

    def fetch_business(self, provider_business_id: str) -> NormalizedBusiness | None: ...

    def fetch_offers(self, provider_business_id: str) -> list[NormalizedOffer]: ...


def require_configured(adapter: ProviderAdapter) -> None:
    if not adapter.configured():
        raise ProviderNotConfigured(
            f"{adapter.name} is not configured. Add the provider API key in environment settings."
        )
