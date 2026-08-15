from collections.abc import Generator

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.feature_flags import FeatureFlags, flags_from_settings
from app.core.security import AdminKeyAuth, Principal
from app.db.session import get_db
from app.services.admin_service import AdminService
from app.services.deal_service import DealService
from app.services.venue_service import VenueService
from app.workers.queue import JobQueue, get_queue


def settings_dep() -> Settings:
    return get_settings()


def flags_dep(settings: Settings = Depends(settings_dep)) -> FeatureFlags:
    return flags_from_settings(settings)


def db_dep() -> Generator[Session, None, None]:
    yield from get_db()


def deal_service_dep(db: Session = Depends(db_dep), flags: FeatureFlags = Depends(flags_dep)) -> DealService:
    return DealService(db, flags)


def venue_service_dep(db: Session = Depends(db_dep), flags: FeatureFlags = Depends(flags_dep)) -> VenueService:
    return VenueService(db, flags)


def admin_service_dep(db: Session = Depends(db_dep), flags: FeatureFlags = Depends(flags_dep)) -> AdminService:
    return AdminService(db, flags)


def queue_dep(settings: Settings = Depends(settings_dep)) -> JobQueue:
    return get_queue(settings.queue_backend, settings.redis_url)


def admin_principal(
    settings: Settings = Depends(settings_dep),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    authorization: str | None = Header(default=None),
) -> Principal:
    presented = x_admin_key
    if not presented and authorization and authorization.lower().startswith("bearer "):
        presented = authorization.split(" ", 1)[1]
    return AdminKeyAuth(settings.admin_api_key).authenticate_admin(presented)
