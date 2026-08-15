from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class FeatureFlags:
    deal_score: bool
    maps: bool
    accounts: bool
    community_verification: bool
    flash_deals: bool
    restaurant_portal: bool
    ai_extraction: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "deal_score": self.deal_score,
            "maps": self.maps,
            "accounts": self.accounts,
            "community_verification": self.community_verification,
            "flash_deals": self.flash_deals,
            "restaurant_portal": self.restaurant_portal,
            "ai_extraction": self.ai_extraction,
        }


def flags_from_settings(settings: Settings) -> FeatureFlags:
    return FeatureFlags(
        deal_score=settings.feature_deal_score,
        maps=settings.feature_maps,
        accounts=settings.feature_accounts,
        community_verification=settings.feature_community_verification,
        flash_deals=settings.feature_flash_deals,
        restaurant_portal=settings.feature_restaurant_portal,
        ai_extraction=settings.feature_ai_extraction,
    )
