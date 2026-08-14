from datetime import datetime, timedelta, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.config import get_settings
from app.db.deps import get_db
from app.models.device import Device
from app.models.device_credential import DeviceCredential
from app.models.enums import CredentialKind, PairingState, UserRole
from app.schemas.common import Page
from app.schemas.device import (
    DeviceCreate,
    DeviceCreateOut,
    DeviceListOut,
    DeviceOut,
)
from app.services import audit
from app.services.credentials import generate_token, hash_token
from app.services.tenant_repo import TenantContext, TenantRepo

router = APIRouter(prefix="/devices", tags=["devices"])


async def _create_device_with_pairing_token(
    db: AsyncSession, ctx: TenantContext, name: str
) -> tuple[Device, str]:
    repo = TenantRepo(db, ctx)
    device = repo.stamp_tenant(Device(name=name))
    db.add(device)
    await db.flush()

    settings = get_settings()
    raw_token = generate_token()
    pairing_expires_at = datetime.now(UTC) + timedelta(seconds=settings.pairing_token_ttl_seconds)
    db.add(
        DeviceCredential(
            device_id=device.id,
            kind=CredentialKind.pairing,
            token_hash=hash_token(raw_token),
            expires_at=pairing_expires_at,
        )
    )
    return device, raw_token


@router.get("", response_model=DeviceListOut)
async def list_devices(
    q: str | None = Query(default=None, description="filter by name substring"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    repo = TenantRepo(db, ctx)
    stmt = repo.scoped(Device)
    if q:
        stmt = stmt.where(Device.name.ilike(f"%{q}%"))

    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()

    # Online first, then most-recently-seen, then name -- IMPLEMENTATION_PLAN §1.3.
    stmt = stmt.order_by(
        Device.online.desc(), Device.last_seen_at.desc().nulls_last(), Device.name.asc()
    ).limit(limit).offset(offset)
    devices = (await db.execute(stmt)).scalars().all()

    return DeviceListOut(
        items=[DeviceOut.model_validate(d) for d in devices],
        page=Page(total=total, limit=limit, offset=offset),
    )


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    repo = TenantRepo(db, ctx)
    device = await repo.get_or_404(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")
    return DeviceOut.model_validate(device)


@router.post("", response_model=DeviceCreateOut, status_code=status.HTTP_201_CREATED)
async def create_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    repo = TenantRepo(db, ctx)
    device = repo.stamp_tenant(Device(name=body.name))
    db.add(device)
    await db.flush()

    settings = get_settings()
    raw_token = generate_token()
    pairing_expires_at = datetime.now(UTC) + timedelta(seconds=settings.pairing_token_ttl_seconds)
    db.add(
        DeviceCredential(
            device_id=device.id,
            kind=CredentialKind.pairing,
            token_hash=hash_token(raw_token),
            expires_at=pairing_expires_at,
        )
    )

    await audit.record(
        db, ctx, "device.create", target_device_id=device.id, payload={"name": device.name}
    )
    await db.commit()
    await db.refresh(device)
    return DeviceCreateOut(device=DeviceOut.model_validate(device), pairing_token=raw_token)


@router.post("/{device_id}/credential/rotate", response_model=DeviceCreateOut)
async def rotate_credential(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    """Issue a fresh single-use pairing token, revoking any prior credential.

    The device must re-pair with the new token; its existing live gateway
    connection (if any) is torn down because the gateway checks credential
    validity on every frame, not just at connect time (IMPLEMENTATION_PLAN §2.2).
    """
    repo = TenantRepo(db, ctx)
    device = await repo.get_or_404(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")

    now = datetime.now(UTC)
    await db.execute(
        DeviceCredential.__table__.update()
        .where(DeviceCredential.device_id == device.id, DeviceCredential.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    settings = get_settings()
    raw_token = generate_token()
    db.add(
        DeviceCredential(
            device_id=device.id,
            kind=CredentialKind.pairing,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(seconds=settings.pairing_token_ttl_seconds),
        )
    )
    device.pairing_state = PairingState.pending
    await audit.record(db, ctx, "device.credential.rotate", target_device_id=device.id)
    await db.commit()
    await db.refresh(device)
    return DeviceCreateOut(device=DeviceOut.model_validate(device), pairing_token=raw_token)


@router.post("/{device_id}/credential/revoke")
async def revoke_credential(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    repo = TenantRepo(db, ctx)
    device = await repo.get_or_404(Device, device_id)
    if device is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "device not found")

    now = datetime.now(UTC)
    await db.execute(
        DeviceCredential.__table__.update()
        .where(DeviceCredential.device_id == device.id, DeviceCredential.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    device.pairing_state = PairingState.revoked
    await audit.record(db, ctx, "device.credential.revoke", target_device_id=device.id)
    await db.commit()
    return {"ok": True}
