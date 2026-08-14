from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.services.tenant_repo import TenantContext, TenantRepo


async def get_tenant_device_or_404(db: AsyncSession, ctx: TenantContext, device_id: UUID) -> Device:
    """Every /devices/{id}/<child-resource> route needs this same check --
    child tables (telemetry_sample, fault, log_bundle, backup, ...) carry
    device_id but not tenant_id directly, so tenant scoping has to happen
    via the parent device first (IMPLEMENTATION_PLAN §6)."""
    repo = TenantRepo(db, ctx)
    device = await repo.get_or_404(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    return device
