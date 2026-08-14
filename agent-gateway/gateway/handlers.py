"""Per-frame-type business logic, kept out of servicer.py so the gRPC glue
stays readable. Each handler takes the open DB session for this frame and
the device it belongs to.
"""

import logging
import uuid
from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alarm import Alarm, AlarmRule
from app.models.backup import Backup
from app.models.device import Device
from app.models.enums import AlarmState, FaultSeverity
from app.models.fault import Fault
from app.models.log_bundle import LogBundle
from app.models.telemetry import TelemetrySample
from app.models.update import DeviceRolloutStatus, RolloutStatus, UpdateRollout, UpdateRolloutDevice
from app.services.storage import new_object_id, object_key, presigned_upload_url
from zionhq.agent_pb2 import FaultEvent, Location, LogUploadRequest, TelemetryBatch

logger = logging.getLogger("gateway.handlers")

_SEVERITY_MAP = {
    FaultEvent.INFO: FaultSeverity.info,
    FaultEvent.WARN: FaultSeverity.warn,
    FaultEvent.CRITICAL: FaultSeverity.critical,
}


def _ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


async def handle_telemetry_batch(
    session: AsyncSession, device: Device, batch: TelemetryBatch
) -> None:
    for sample in batch.samples:
        session.add(
            TelemetrySample(
                device_id=device.id,
                recorded_at=_ms_to_dt(sample.recorded_at_unix_ms),
                metric=sample.metric,
                value=sample.value,
                tags=dict(sample.tags),
            )
        )
    if batch.HasField("location") and (batch.location.lat or batch.location.lon):
        loc = batch.location
        recorded_at = (
            _ms_to_dt(loc.recorded_at_unix_ms) if loc.recorded_at_unix_ms else datetime.now(UTC)
        )
        session.add(
            TelemetrySample(
                device_id=device.id,
                recorded_at=recorded_at,
                metric="location",
                value=0.0,
                tags={
                    "lat": str(loc.lat),
                    "lon": str(loc.lon),
                    "accuracy_m": str(loc.accuracy_m),
                    "source": Location.Source.Name(loc.source),
                },
            )
        )
    await session.flush()


async def handle_log_upload_request(
    session: AsyncSession, device: Device, req: LogUploadRequest
) -> tuple[str, str, int]:
    """Creates the LogBundle/Backup row eagerly (optimistic -- there is no
    upload-complete callback in this proto version, see gateway/servicer.py)
    and returns (request_ref, presigned_put_url, expires_in_s) for the
    SignedUploadUrl response frame.
    """
    object_id = new_object_id()
    kind = "backup" if req.kind == LogUploadRequest.BACKUP else "log_bundle"
    key = object_key(kind, str(device.id), str(object_id))
    now = datetime.now(UTC)

    if req.kind == LogUploadRequest.BACKUP:
        session.add(
            Backup(
                id=object_id,
                device_id=device.id,
                storage_url=key,
                size_bytes=req.size_bytes_estimate,
                created_at=now,
            )
        )
    else:
        session.add(
            LogBundle(
                id=object_id,
                device_id=device.id,
                storage_url=key,
                size_bytes=req.size_bytes_estimate,
                uploaded_at=now,
                time_range_start=_ms_to_dt(req.time_range_start_unix_ms),
                time_range_end=_ms_to_dt(req.time_range_end_unix_ms),
            )
        )
    await session.flush()

    expires_in = 900
    return str(object_id), presigned_upload_url(key, expires_in=expires_in), expires_in


async def _evaluate_fault_alarms(session: AsyncSession, device: Device, fault: Fault) -> None:
    rules = (
        await session.execute(
            select(AlarmRule).where(
                AlarmRule.tenant_id == device.tenant_id, AlarmRule.enabled.is_(True)
            )
        )
    ).scalars().all()
    for rule in rules:
        cond = rule.condition or {}
        if cond.get("kind") != "fault_code":
            continue
        severity_filter = cond.get("severity")
        code_filter = cond.get("code")
        if severity_filter and severity_filter != fault.severity.value:
            continue
        if code_filter and code_filter != fault.code:
            continue
        session.add(
            Alarm(
                alarm_rule_id=rule.id,
                device_id=device.id,
                state=AlarmState.active,
                triggered_at=fault.raised_at,
                source_fault_id=fault.id,
            )
        )


async def handle_fault_event(session: AsyncSession, device: Device, event: FaultEvent) -> None:
    if event.kind == FaultEvent.CLEARED:
        code = event.fault_code_ref or event.code
        open_fault = (
            await session.execute(
                select(Fault)
                .where(Fault.device_id == device.id, Fault.code == code, Fault.cleared_at.is_(None))
                .order_by(Fault.raised_at.desc())
            )
        ).scalars().first()
        if open_fault:
            open_fault.cleared_at = _ms_to_dt(event.at_unix_ms)
        return

    fault = Fault(
        device_id=device.id,
        code=event.code,
        severity=_SEVERITY_MAP.get(event.severity, FaultSeverity.info),
        message=event.message,
        raised_at=_ms_to_dt(event.at_unix_ms),
    )
    session.add(fault)
    await session.flush()
    await _evaluate_fault_alarms(session, device, fault)


async def handle_command_ack(
    session: AsyncSession, device: Device, command_id: str, success: bool, error: str
) -> None:
    if command_id.startswith("update:"):
        rollout_id = uuid.UUID(command_id.split(":", 2)[1])
        row = await session.get(
            UpdateRolloutDevice, {"rollout_id": rollout_id, "device_id": device.id}
        )
        if row is None:
            logger.warning("command_ack for unknown rollout row %s", command_id)
            return
        row.status = DeviceRolloutStatus.succeeded if success else DeviceRolloutStatus.failed
        row.applied_at = datetime.now(UTC)
        row.error = None if success else error

        siblings = (
            await session.execute(
                select(UpdateRolloutDevice).where(UpdateRolloutDevice.rollout_id == rollout_id)
            )
        ).scalars().all()
        terminal = (DeviceRolloutStatus.succeeded, DeviceRolloutStatus.failed)
        all_terminal = all(s.status in terminal for s in siblings)
        if all_terminal:
            rollout = await session.get(UpdateRollout, rollout_id)
            if rollout:
                rollout.status = RolloutStatus.completed
                rollout.completed_at = datetime.now(UTC)
    elif command_id.startswith("restore:"):
        backup_id = uuid.UUID(command_id.split(":", 2)[1])
        backup = await session.get(Backup, backup_id)
        if backup and success:
            backup.restored_at = datetime.now(UTC)
    else:
        logger.info("command_ack %s success=%s error=%s", command_id, success, error)
