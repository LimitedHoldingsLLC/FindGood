from fastapi import APIRouter, Depends

from app.api.dependencies import settings_dep
from app.api.schemas import AdminSessionIn
from app.core.config import Settings
from app.core.security import AdminKeyAuth

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/session")
def admin_session(payload: AdminSessionIn, settings: Settings = Depends(settings_dep)) -> dict:
    principal = AdminKeyAuth(settings.admin_api_key).authenticate_admin(payload.api_key)
    return {"ok": True, "subject": principal.subject}
