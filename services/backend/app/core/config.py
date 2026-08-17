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

    crawler_user_agent: str = "FindGoodBot/0.1 (+https://findgood.food/bot)"
    crawler_request_timeout_seconds: int = 10
    crawler_max_response_bytes: int = 1_048_576
    crawler_max_concurrency: int = 2
    crawler_default_rate_limit_per_minute: int = 6
    crawler_respect_robots_txt: bool = True

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120

    @field_validator("database_url")
    @classmethod
    def _normalize_db(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def cors_origins(self) -> list[str]:
        return [part.strip() for part in self.cors_allowed_origins.split(",") if part.strip()]

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
