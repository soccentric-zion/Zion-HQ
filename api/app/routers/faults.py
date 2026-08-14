from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import UserRole
from app.models.fault import Fault
from app.schemas.common import Page
from app.schemas.fault import FaultListOut, FaultOut
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/faults", tags=["faults"])


@router.get("", response_model=FaultListOut)
async def list_faults(
    device_id: UUID,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(Fault).where(Fault.device_id == device_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Fault.raised_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()

    return FaultListOut(
        items=[FaultOut.model_validate(r) for r in rows],
        page=Page(total=total, limit=limit, offset=offset),
    )
