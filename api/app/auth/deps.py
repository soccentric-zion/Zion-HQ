from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from app.auth.session import InvalidSession, verify_session_token
from app.models.enums import UserRole
from app.services.tenant_repo import TenantContext

SESSION_COOKIE_NAME = "zionhq_session"

_ROLE_RANK = {UserRole.viewer: 0, UserRole.operator: 1, UserRole.admin: 2}


async def get_current_context(request: Request) -> TenantContext:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "not authenticated")
    try:
        claims = verify_session_token(token)
    except InvalidSession as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session") from exc
    return TenantContext(
        tenant_id=UUID(claims["tenant_id"]),
        user_id=UUID(claims["sub"]),
        role=claims["role"],
    )


def require_role(minimum: UserRole):
    """Dependency factory: 401 if unauthenticated, 403 if role too low.

    Role permission matrix is IMPLEMENTATION_PLAN §1.2's table -- routers
    pick the minimum role per action from that table, this just enforces
    the ordering (viewer < operator < admin).
    """

    async def _dep(ctx: TenantContext = Depends(get_current_context)) -> TenantContext:
        try:
            actual = UserRole(ctx.role)
        except ValueError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "unknown role") from exc
        if _ROLE_RANK[actual] < _ROLE_RANK[minimum]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"requires {minimum.value} role")
        return ctx

    return _dep
