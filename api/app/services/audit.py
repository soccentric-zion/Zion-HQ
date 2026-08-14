from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.services.tenant_repo import TenantContext


async def record(
    session: AsyncSession,
    ctx: TenantContext,
    action: str,
    *,
    target_device_id=None,
    payload: dict | None = None,
) -> None:
    """Write an audit_log row.

    Called directly (not via TenantRepo) because writes here should happen
    even on paths that otherwise avoid extra indirection -- audit logging is
    cross-cutting per IMPLEMENTATION_PLAN §6, not tied to one repo's CRUD
    surface. Callers are still responsible for committing the session.
    """
    session.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            actor_user_id=ctx.user_id,
            action=action,
            target_device_id=target_device_id,
            payload=payload or {},
        )
    )
