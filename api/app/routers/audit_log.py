from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.audit_log import AuditLog
from app.models.enums import UserRole
from app.schemas.audit_log import AuditLogListOut, AuditLogOut
from app.schemas.common import Page
from app.services.tenant_repo import TenantContext, TenantRepo

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=AuditLogListOut)
async def list_audit_log(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    stmt = repo.scoped(AuditLog)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return AuditLogListOut(
        items=[AuditLogOut.model_validate(r) for r in rows],
        page=Page(total=total, limit=limit, offset=offset),
    )
