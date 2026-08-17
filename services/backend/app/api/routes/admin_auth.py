from fastapi import APIRouter, Depends

from app.api.dependencies import admin_auth_dep, admin_client_key
from app.api.schemas import AdminSessionIn, AdminSessionOut
from app.core.security import AdminAuth

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/session")
def admin_session(
    payload: AdminSessionIn,
    auth: AdminAuth = Depends(admin_auth_dep),
    client_key: str = Depends(admin_client_key),
) -> AdminSessionOut:
    principal = auth.login(payload.username, payload.password, client_key=client_key)
    token, expires_at = auth.issue_session(principal)
    return AdminSessionOut(ok=True, subject=principal.subject, token=token, expires_at=expires_at)
