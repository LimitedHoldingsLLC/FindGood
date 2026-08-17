"""Yelp Fusion adapter.

Uses the official Yelp Fusion REST API. Yelp-specific fields stay in this
module; the rest of FindGood only sees NormalizedBusiness.

Licensing note: Yelp terms typically restrict caching duration, redistribution,
and display of reviews/photos/ratings. We keep the Yelp business id and
identity fields, store ratings in provider metadata, and do not present Yelp
reviews as FindGood reviews.
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

SEARCH_URL = "https://api.yelp.com/v3/businesses/search"
DETAIL_URL = "https://api.yelp.com/v3/businesses/{business_id}"


class YelpAdapter:
    name = "yelp"

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
        params: dict[str, Any] = {
            "term": query.text or "restaurants",
            "categories": "restaurants",
            "limit": min(max(query.max_results, 1), 50),
        }
        if query.latitude is not None and query.longitude is not None:
            params["latitude"] = query.latitude
            params["longitude"] = query.longitude
            params["radius"] = min(query.radius_meters, 40000)
        elif query.city:
            params["location"] = query.city
        else:
            params["location"] = "Los Angeles, CA"
        data = self._get(f"{SEARCH_URL}?{urlencode(params)}")
        results: list[NormalizedBusiness] = []
        for row in data.get("businesses") or []:
            normalized = self._normalize(row)
            if normalized:
                results.append(normalized)
        return results

    def fetch_business(self, provider_business_id: str) -> NormalizedBusiness | None:
        self._ensure()
        data = self._get(DETAIL_URL.format(business_id=provider_business_id))
        return self._normalize(data)

    def fetch_offers(self, provider_business_id: str) -> list[NormalizedOffer]:
        return []

    def _ensure(self) -> None:
        if not self.configured():
            raise ProviderNotConfigured("Yelp is not configured. Set YELP_API_KEY to use this provider.")
        if self.calls_used >= self.max_calls_per_run:
            raise ProviderError("Yelp call budget for this run is exhausted")

    def _get(self, url: str) -> dict[str, Any]:
        self.calls_used += 1
        fetched = self.client.get(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            validate_url=True,
        )
        if fetched.http_status in {401, 403}:
            raise ProviderAuthenticationError("Yelp rejected the API key")
        if fetched.http_status == 429:
            raise ProviderRateLimited("Yelp rate limited this request")
        if fetched.http_status >= 400:
            raise ProviderError(f"Yelp HTTP {fetched.http_status}")
        import json

        return json.loads(fetched.content.decode("utf-8"))

    def _normalize(self, row: dict[str, Any]) -> NormalizedBusiness | None:
        yelp_id = row.get("id")
        name = row.get("name")
        loc = row.get("location") or {}
        coords = row.get("coordinates") or {}
        location = location_from_parts(
            address_line1=(loc.get("address1") or None),
            city=loc.get("city"),
            region=loc.get("state"),
            postal_code=loc.get("zip_code"),
            latitude=coords.get("latitude"),
            longitude=coords.get("longitude"),
            country=loc.get("country") or "US",
            formatted=", ".join(loc.get("display_address") or []),
        )
        if not yelp_id or not name or location is None:
            return None
        rating = row.get("rating")
        cats = [item.get("alias") or item.get("title") for item in (row.get("categories") or [])]
        return NormalizedBusiness(
            provider="yelp",
            provider_business_id=str(yelp_id),
            name=str(name)[:200],
            phone=row.get("display_phone") or row.get("phone"),
            website_url=None,
            categories=[str(c) for c in cats if c][:12],
            location=location,
            provider_url=row.get("url"),
            rating=Decimal(str(rating)) if rating is not None else None,
            review_count=row.get("review_count"),
            retrieved_at=datetime.now(UTC),
            extra={"raw_keys": sorted(row.keys())},
        )
