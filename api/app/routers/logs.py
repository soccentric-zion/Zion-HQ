from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.enums import UserRole
from app.models.log_bundle import LogBundle
from app.schemas.common import Page
from app.schemas.log_bundle import DownloadUrlOut, LogBundleListOut, LogBundleOut
from app.services.device_scope import get_tenant_device_or_404
from app.services.storage import presigned_download_url
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/logs", tags=["logs"])


@router.get("", response_model=LogBundleListOut)
async def list_log_bundles(
    device_id: UUID,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(LogBundle).where(LogBundle.device_id == device_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(LogBundle.uploaded_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()

    return LogBundleListOut(
        items=[LogBundleOut.model_validate(r) for r in rows],
        page=Page(total=total, limit=limit, offset=offset),
    )


@router.get("/{bundle_id}/download", response_model=DownloadUrlOut)
async def download_log_bundle(
    device_id: UUID,
    bundle_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    await get_tenant_device_or_404(db, ctx, device_id)
    bundle = (
        await db.execute(
            select(LogBundle).where(LogBundle.id == bundle_id, LogBundle.device_id == device_id)
        )
    ).scalar_one_or_none()
    if bundle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "log bundle not found")
    return DownloadUrlOut(download_url=presigned_download_url(bundle.storage_url))
