from collections.abc import Generator

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.feature_flags import FeatureFlags, flags_from_settings
from app.core.security import AdminAuth, Principal, get_login_attempt_guard
from app.db.session import get_db
from app.services.admin_service import AdminService
from app.services.deal_service import DealService
from app.services.ops_service import OpsService
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


def ops_service_dep(
    db: Session = Depends(db_dep),
    flags: FeatureFlags = Depends(flags_dep),
    settings: Settings = Depends(settings_dep),
    queue: JobQueue = Depends(queue_dep),
) -> OpsService:
    return OpsService(db, settings, flags, queue)


def admin_auth_dep(settings: Settings = Depends(settings_dep)) -> AdminAuth:
    return AdminAuth(
        username=settings.admin_username,
        password=settings.admin_password,
        signing_key=settings.admin_api_key,
        session_ttl_seconds=settings.admin_session_ttl_seconds,
        attempt_guard=get_login_attempt_guard(
            settings.admin_login_max_failures,
            settings.admin_login_window_seconds,
            settings.admin_login_lockout_seconds,
            settings.admin_login_global_max_failures,
            not settings.is_test,
        ),
    )


def admin_client_key(request: Request, settings: Settings = Depends(settings_dep)) -> str:
    if settings.is_production:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()[:128]
    return request.client.host if request.client else "unknown"


def admin_principal(
    auth: AdminAuth = Depends(admin_auth_dep),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    authorization: str | None = Header(default=None),
) -> Principal:
    bearer: str | None = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1]
    return auth.authenticate_request(bearer_token=bearer, api_key=x_admin_key)
