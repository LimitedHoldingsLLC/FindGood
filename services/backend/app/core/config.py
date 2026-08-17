from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Render and Docker often emit postgres://; SQLAlchemy 2 + psycopg3 need a driver name."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FindGood"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_format: Literal["console", "json"] = "console"

    api_base_url: str = "http://localhost:8000"
    web_base_url: str = "http://localhost:3000"
    canonical_host: str = "findgood.food"
    acquisition_host: str = "happyhour.food"

    database_url: str = "postgresql+psycopg://findgood:findgood@localhost:5432/findgood"
    redis_url: str = "redis://localhost:6379/0"
    queue_backend: Literal["redis", "memory"] = "redis"

    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    admin_username: str = "admin"
    admin_password: str = "change-me-to-a-strong-admin-password"
    admin_api_key: str = "change-me-to-a-long-random-admin-key"
    admin_session_ttl_seconds: int = 43_200
    admin_login_max_failures: int = 5
    admin_login_window_seconds: int = 900
    admin_login_lockout_seconds: int = 900
    admin_login_global_max_failures: int = 25

    feature_deal_score: bool = True
    feature_maps: bool = False
    feature_accounts: bool = False
    feature_community_verification: bool = False
    feature_flash_deals: bool = False
    feature_restaurant_portal: bool = False
    feature_ai_extraction: bool = False

    crawler_user_agent: str = "FindGoodBot/1.0 (+https://findgood.food/bot)"
    crawler_request_timeout_seconds: int = 15
    crawler_max_response_bytes: int = 1_048_576
    crawler_max_concurrency: int = 10
    crawler_domain_concurrency: int = 1
    crawler_default_rate_limit_per_minute: int = 6
    crawler_respect_robots_txt: bool = True
    crawler_max_pages_per_domain: int = 10
    crawler_max_pages_per_run: int = 40
    crawler_max_depth: int = 2
    crawler_max_redirects: int = 3
    crawler_retry_count: int = 3
    crawler_per_domain_delay_seconds: float = 1.0
    crawler_allowed_content_types: str = "text/html,application/xhtml+xml,application/json,text/plain"

    google_places_api_key: str = ""
    google_places_max_calls_per_run: int = 20
    google_places_enabled: bool = True

    yelp_api_key: str = ""
    yelp_max_calls_per_run: int = 20
    yelp_enabled: bool = True

    opentable_api_key: str = ""
    opentable_enabled: bool = False

    business_stale_after_days: int = 30
    hours_stale_after_days: int = 14
    happy_hour_stale_after_days: int = 7
    special_stale_after_days: int = 3
    contact_stale_after_days: int = 21
    aging_ratio: float = 0.6

    admin_bulk_limit: int = 50
    admin_export_row_limit: int = 5_000

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120

    @property
    def crawler_allowed_content_type_list(self) -> list[str]:
        return [part.strip().casefold() for part in self.crawler_allowed_content_types.split(",") if part.strip()]

    @field_validator("database_url")
    @classmethod
    def _normalize_db(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origins(self) -> list[str]:
        origins = [part.strip().rstrip("/") for part in self.cors_allowed_origins.split(",") if part.strip()]
        if self.is_production:
            for extra in (
                "https://findgood.food",
                "https://www.findgood.food",
                "https://findgood.vercel.app",
            ):
                if extra not in origins:
                    origins.append(extra)
        return origins

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
