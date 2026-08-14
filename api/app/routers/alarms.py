from datetime import datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_role
from app.db.deps import get_db
from app.models.alarm import Alarm, AlarmRule
from app.models.device import Device
from app.models.device_alarm import DeviceAlarm
from app.models.enums import AlarmState, UserRole
from app.schemas.alarm import AlarmOut, AlarmRuleCreate, AlarmRuleOut
from app.schemas.common import Page
from app.schemas.device_alarm import DeviceAlarmIn, DeviceAlarmListOut, DeviceAlarmOut
from app.services import audit
from app.services.device_scope import get_tenant_device_or_404
from app.services.tenant_repo import TenantContext, TenantRepo

device_alarms_router = APIRouter(prefix="/devices/{device_id}/alarms", tags=["alarms"])
alarms_router = APIRouter(prefix="/alarms", tags=["alarms"])
alarm_rules_router = APIRouter(prefix="/alarm-rules", tags=["alarms"])

# 4-byte alarm code packing (device-reported alarms, R3 ingest path).
# The code is a big-endian uint32 where:
#   byte 0 (most significant) = major_id
#   byte 1                   = sub_section
#   byte 2                   = fault_type
#   byte 3 (least significant) = severity
# Example: 0x01020304 -> major_id=1, sub_section=2, fault_type=3, severity=4.
# This byte order MUST match the daemon's `alarms_encode` packing.


def _decode_alarm_code(code: int) -> tuple[int, int, int, int]:
    """Unpack a 4-byte alarm code into (major_id, sub_section, fault_type, severity)."""
    return (
        (code >> 24) & 0xFF,
        (code >> 16) & 0xFF,
        (code >> 8) & 0xFF,
        code & 0xFF,
    )


@device_alarms_router.get("", response_model=DeviceAlarmListOut)
async def list_device_alarms(
    device_id: UUID,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    """List device-reported alarms from the ``alarms`` table (R3).

    Returns rows for the tenant's device, newest first, with the decoded
    4-byte alarm scheme fields.
    """
    await get_tenant_device_or_404(db, ctx, device_id)

    stmt = select(DeviceAlarm).where(DeviceAlarm.device_id == device_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(DeviceAlarm.triggered_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()

    return DeviceAlarmListOut(
        items=[DeviceAlarmOut.model_validate(r) for r in rows],
        page=Page(total=total, limit=limit, offset=offset),
    )


@device_alarms_router.post(
    "", response_model=DeviceAlarmOut, status_code=status.HTTP_201_CREATED
)
async def ingest_device_alarm(
    device_id: UUID,
    body: DeviceAlarmIn,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Ingest a device-reported 4-byte alarm into the ``alarms`` table (R3).

    The device must belong to the caller's tenant (scoped via the parent
    device). ``alarm_code`` is a hex string (e.g. ``"0x01020304"``) decoded
    into major_id / sub_section / fault_type / severity using the byte order
    documented at the top of this module. The row is created in the ``active``
    state. ``triggered_at`` is the device-side timestamp, stored verbatim.
    """
    await get_tenant_device_or_404(db, ctx, device_id)

    try:
        code = int(body.alarm_code, 16)
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "alarm_code must be a hex string e.g. '0x01020304'",
        ) from exc
    if code < 0 or code > 0xFFFFFFFF:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "alarm_code must fit in 4 bytes (0x00000000..0xffffffff)",
        )

    major_id, sub_section, fault_type, severity = _decode_alarm_code(code)

    alarm = DeviceAlarm(
        device_id=device_id,
        major_id=major_id,
        sub_section=sub_section,
        fault_type=fault_type,
        severity=severity,
        alarm_code=code,
        state=AlarmState.active,
        triggered_at=body.triggered_at,
    )
    db.add(alarm)
    await db.flush()
    await audit.record(
        db,
        ctx,
        "alarm.ingest",
        target_device_id=device_id,
        payload={"alarm_code": body.alarm_code},
    )
    await db.commit()
    await db.refresh(alarm)
    return DeviceAlarmOut.model_validate(alarm)


async def _get_tenant_alarm_or_404(db: AsyncSession, ctx: TenantContext, alarm_id: UUID) -> Alarm:
    row = (
        await db.execute(
            select(Alarm).join(Device, Alarm.device_id == Device.id).where(
                Alarm.id == alarm_id, Device.tenant_id == ctx.tenant_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "alarm not found")
    return row


@alarms_router.post("/{alarm_id}/acknowledge", response_model=AlarmOut)
async def acknowledge_alarm(
    alarm_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    alarm = await _get_tenant_alarm_or_404(db, ctx, alarm_id)
    alarm.state = AlarmState.acknowledged
    alarm.acknowledged_at = datetime.now(UTC)
    alarm.acknowledged_by = ctx.user_id
    await audit.record(db, ctx, "alarm.acknowledge", target_device_id=alarm.device_id)
    await db.commit()
    await db.refresh(alarm)
    return AlarmOut.model_validate(alarm)


@alarms_router.post("/{alarm_id}/resolve", response_model=AlarmOut)
async def resolve_alarm(
    alarm_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    alarm = await _get_tenant_alarm_or_404(db, ctx, alarm_id)
    alarm.state = AlarmState.resolved
    alarm.resolved_at = datetime.now(UTC)
    await audit.record(db, ctx, "alarm.resolve", target_device_id=alarm.device_id)
    await db.commit()
    await db.refresh(alarm)
    return AlarmOut.model_validate(alarm)


@device_alarms_router.post("/{alarm_id}/clear", response_model=DeviceAlarmOut)
async def clear_device_alarm(
    device_id: UUID,
    alarm_id: UUID,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    """Device-scoped "clear" verb for a device-reported alarm (R3).

    ``clear`` is semantically identical to ``resolve``: the alarm's state
    transitions ``active -> resolved`` and ``resolved_at`` is stamped. There
    is no separate ``cleared`` state -- the existing ``AlarmState`` enum has
    only ``active``/``acknowledged``/``resolved``, and ``clear`` reuses
    ``resolved`` (F5 equivalence). The alarm must belong to the device in
    the path and to the caller's tenant.
    """
    await get_tenant_device_or_404(db, ctx, device_id)
    row = (
        await db.execute(
            select(DeviceAlarm).where(
                DeviceAlarm.id == alarm_id, DeviceAlarm.device_id == device_id
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "alarm not found")
    row.state = AlarmState.resolved
    row.resolved_at = datetime.now(UTC)
    await audit.record(db, ctx, "alarm.clear", target_device_id=device_id)
    await db.commit()
    await db.refresh(row)
    return DeviceAlarmOut.model_validate(row)


@alarm_rules_router.get("", response_model=list[AlarmRuleOut])
async def list_alarm_rules(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.viewer)),
):
    repo = TenantRepo(db, ctx)
    rows = (await db.execute(repo.scoped(AlarmRule).order_by(AlarmRule.name))).scalars().all()
    return [AlarmRuleOut.model_validate(r) for r in rows]


@alarm_rules_router.post("", response_model=AlarmRuleOut, status_code=status.HTTP_201_CREATED)
async def create_alarm_rule(
    body: AlarmRuleCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_role(UserRole.operator)),
):
    repo = TenantRepo(db, ctx)
    rule = repo.stamp_tenant(
        AlarmRule(
            name=body.name,
            condition=body.condition,
            notify_channels=body.notify_channels,
            enabled=body.enabled,
        )
    )
    db.add(rule)
    await audit.record(db, ctx, "alarm_rule.create", payload={"name": body.name})
    await db.commit()
    await db.refresh(rule)
    return AlarmRuleOut.model_validate(rule)
