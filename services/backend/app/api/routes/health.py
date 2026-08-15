from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import db_dep, settings_dep
from app.api.schemas import FeatureFlagsOut, HealthOut, ReadyOut
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.core.feature_flags import flags_from_settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(settings: Settings = Depends(settings_dep)) -> HealthOut:
    return HealthOut(status="ok", service=settings.app_name)


@router.get("/ready", response_model=ReadyOut)
def ready(
    db: Session = Depends(db_dep),
    settings: Settings = Depends(settings_dep),
) -> ReadyOut:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Database is not ready") from exc
    queue_ok = True
    if settings.queue_backend == "redis":
        try:
            import redis

            redis.Redis.from_url(settings.redis_url).ping()
        except Exception as exc:
            raise ServiceUnavailableError("Queue is not ready") from exc
    return ReadyOut(status="ok", database=True, queue=queue_ok)


@router.get("/api/v1/flags", response_model=FeatureFlagsOut)
def flags(settings: Settings = Depends(settings_dep)) -> FeatureFlagsOut:
    return FeatureFlagsOut(flags=flags_from_settings(settings).as_dict())
