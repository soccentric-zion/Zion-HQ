from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.backup import Backup
from app.models.enums import CommandKind, UserRole
from app.models.pending_command import PendingCommand
from app.schemas.backup import BackupListOut, BackupOut
from app.schemas.common import Page
from app.services import audit
from app.services.device_scope import get_tenant_device_or_404
from app.services.storage import presigned_download_url
from app.services.tenant_repo import TenantContext

router = APIRouter(prefix="/devices/{device_id}/backups", tags=["backups"])


@router.get("", response_model=BackupListOut)
async def list_backups(
    device_id: UUID,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(Backup).where(Backup.device_id == device_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(Backup.created_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()

    return BackupListOut(
        items=[BackupOut.model_validate(r) for r in rows],
        page=Page(total=total, limit=limit, offset=offset),
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def take_backup_now(
    device_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Queues a TakeBackupNow command; agent-gateway delivers it on the
    device's next heartbeat (cross-process handoff, see PendingCommand) and
    the actual `backup` row is created when the device later uploads the
    blob via a LogUploadRequest(kind=BACKUP) frame.
    """
    await get_tenant_device_or_404(db, ctx, device_id)

    command_id = f"backup:{uuid4()}"
    db.add(
        PendingCommand(
            device_id=device_id, command_id=command_id, kind=CommandKind.take_backup_now
        )
    )
    await audit.record(db, ctx, "device.backup.request", target_device_id=device_id)
    await db.commit()
    return {"ok": True, "command_id": command_id}


@router.post("/{backup_id}/restore", status_code=status.HTTP_202_ACCEPTED)
async def restore_backup(
    device_id: UUID,
    backup_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.admin)),
):
    await get_tenant_device_or_404(db, ctx, device_id)
    stmt = select(Backup).where(Backup.id == backup_id, Backup.device_id == device_id)
    backup = (await db.execute(stmt)).scalar_one_or_none()
    if backup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "backup not found")

    download_url = presigned_download_url(backup.storage_url)
    command_id = f"restore:{backup_id}"
    db.add(
        PendingCommand(
            device_id=device_id,
            command_id=command_id,
            kind=CommandKind.restore,
            payload={"backup_download_url": download_url},
        )
    )
    # Written before the command is even delivered, let alone applied --
    # there must be a record even if the device never acknowledges
    # (ARCHITECTURE.md §6).
    await audit.record(
        db,
        ctx,
        "device.restore.request",
        target_device_id=device_id,
        payload={"backup_id": str(backup_id)},
    )
    await db.commit()
    return {"ok": True, "command_id": command_id}
