"""OpenTable provider boundary.

There is no official public OpenTable API in this repository, and scraping
OpenTable's website would mean fighting access controls — which we will not do.

When partner/feed credentials exist, implement search_businesses against that
authorized channel here. Until then the adapter reports ProviderNotConfigured
so the rest of the system can treat OpenTable like any other optional provider.
"""

from app.core.exceptions import ProviderNotConfigured
from app.domain.ingestion.schemas import NormalizedBusiness, NormalizedOffer
from app.ingestion.providers.base import ProviderSearchQuery

REQUIRED_ACCESS = (
    "OpenTable does not publish a general-purpose restaurant listing API for this "
    "product. Production use needs an authorized partner API, licensed data feed, "
    "or approved integration. Set OPENTABLE_API_KEY only after that access exists, "
    "then implement the official endpoint in this module."
)


class OpenTableAdapter:
    name = "opentable"

    def __init__(self, *, api_key: str = "", enabled: bool = False) -> None:
        self.api_key = api_key.strip()
        self.enabled = enabled

    def configured(self) -> bool:
        # Even with a key present we do not pretend an unofficial scrape works.
        return False

    def search_businesses(self, query: ProviderSearchQuery) -> list[NormalizedBusiness]:
        raise ProviderNotConfigured(REQUIRED_ACCESS)

    def fetch_business(self, provider_business_id: str) -> NormalizedBusiness | None:
        raise ProviderNotConfigured(REQUIRED_ACCESS)

    def fetch_offers(self, provider_business_id: str) -> list[NormalizedOffer]:
        raise ProviderNotConfigured(REQUIRED_ACCESS)
