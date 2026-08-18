"""Tripadvisor Content API adapter.

Uses api.content.tripadvisor.com. There is no HTML scrape in this module.
Tripadvisor typically requires partner approval for a key; without one the
adapter reports not configured, same as any other official provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from app.core.exceptions import ProviderAuthenticationError, ProviderError, ProviderNotConfigured, ProviderRateLimited
from app.domain.ingestion.schemas import NormalizedBusiness, NormalizedOffer
from app.ingestion.http import OutboundHttpClient
from app.ingestion.providers.base import ProviderSearchQuery
from app.ingestion.providers.normalize import location_from_parts

SEARCH_URL = "https://api.content.tripadvisor.com/api/v1/location/search"
DETAIL_URL = "https://api.content.tripadvisor.com/api/v1/location/{location_id}/details"


class TripadvisorAdapter:
    name = "tripadvisor"

    def __init__(
        self,
        *,
        api_key: str,
        client: OutboundHttpClient,
        max_calls_per_run: int = 20,
        enabled: bool = True,
    ) -> None:
        self.api_key = api_key.strip()
        self.client = client
        self.max_calls_per_run = max_calls_per_run
        self.enabled = enabled
        self.calls_used = 0

    def configured(self) -> bool:
        return self.enabled and bool(self.api_key)

    def search_businesses(self, query: ProviderSearchQuery) -> list[NormalizedBusiness]:
        self._ensure()
        text = query.text or "restaurants"
        if query.city:
            text = f"{text} {query.city}"
        params: dict[str, Any] = {
            "key": self.api_key,
            "searchQuery": text,
            "category": "restaurants",
            "language": "en",
        }
        if query.latitude is not None and query.longitude is not None:
            params["latLong"] = f"{query.latitude},{query.longitude}"
        data = self._get(f"{SEARCH_URL}?{urlencode(params)}")
        results: list[NormalizedBusiness] = []
        for row in data.get("data") or []:
            location_id = str(row.get("location_id") or "")
            if not location_id:
                continue
            if row.get("rating") is None and self.calls_used < self.max_calls_per_run:
                detailed = self.fetch_business(location_id)
                if detailed:
                    results.append(detailed)
                continue
            normalized = self._normalize(row)
            if normalized:
                results.append(normalized)
            if len(results) >= query.max_results:
                break
        return results[: query.max_results]

    def fetch_business(self, provider_business_id: str) -> NormalizedBusiness | None:
        self._ensure()
        params = urlencode({"key": self.api_key, "language": "en"})
        data = self._get(f"{DETAIL_URL.format(location_id=provider_business_id)}?{params}")
        return self._normalize(data)

    def fetch_offers(self, provider_business_id: str) -> list[NormalizedOffer]:
        return []

    def _ensure(self) -> None:
        if not self.configured():
            raise ProviderNotConfigured(
                "Tripadvisor is not configured. Set TRIPADVISOR_API_KEY from the official Content API."
            )
        if self.calls_used >= self.max_calls_per_run:
            raise ProviderError("Tripadvisor call budget for this run is exhausted")

    def _get(self, url: str) -> dict[str, Any]:
        self.calls_used += 1
        fetched = self.client.get(url, validate_url=True)
        if fetched.http_status in {401, 403}:
            raise ProviderAuthenticationError("Tripadvisor rejected the API key")
        if fetched.http_status == 429:
            raise ProviderRateLimited("Tripadvisor rate limited this request")
        if fetched.http_status >= 400:
            raise ProviderError(f"Tripadvisor HTTP {fetched.http_status}")
        import json

        return json.loads(fetched.content.decode("utf-8"))

    def _normalize(self, row: dict[str, Any]) -> NormalizedBusiness | None:
        location_id = row.get("location_id")
        name = row.get("name")
        address = row.get("address_obj") or {}
        lat = row.get("latitude")
        lng = row.get("longitude")
        location = location_from_parts(
            address_line1=address.get("street1") or address.get("address_string"),
            city=address.get("city"),
            region=address.get("state"),
            postal_code=address.get("postalcode"),
            latitude=lat,
            longitude=lng,
            country=_country(address.get("country")),
            formatted=address.get("address_string"),
        )
        if not location_id or not name or location is None:
            return None
        rating = row.get("rating")
        reviews = row.get("num_reviews")
        return NormalizedBusiness(
            provider="tripadvisor",
            provider_business_id=str(location_id),
            name=str(name)[:200],
            phone=row.get("phone"),
            website_url=row.get("website"),
            categories=[str(row.get("category") or "restaurant")][:12],
            location=location,
            provider_url=row.get("web_url"),
            rating=Decimal(str(rating)) if rating not in (None, "") else None,
            review_count=int(reviews) if reviews not in (None, "") else None,
            retrieved_at=datetime.now(UTC),
            extra={"raw_keys": sorted(row.keys())},
        )


def _country(value: str | None) -> str:
    if not value:
        return "US"
    if len(value) == 2:
        return value.upper()
    if value.casefold() in {"united states", "usa", "us"}:
        return "US"
    return "US"
