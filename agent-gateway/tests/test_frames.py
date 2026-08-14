import time

from sqlalchemy import select

from app.models.alarm import Alarm, AlarmRule
from app.models.fault import Fault
from app.models.log_bundle import LogBundle
from app.models.telemetry import TelemetrySample
from zionhq.agent_pb2 import (
    AgentFrame,
    FaultEvent,
    Heartbeat,
    LogUploadRequest,
    TelemetryBatch,
    TelemetrySample as PbTelemetrySample,
)
from tests.factories import make_authorized_device_with_credential, make_tenant


def _hb(device_id: str, credential: str) -> Heartbeat:
    return Heartbeat(
        device_id=device_id, credential_token=credential, sent_at_unix_ms=int(time.time() * 1000)
    )


async def test_telemetry_batch_persists_samples(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            telemetry_batch=TelemetryBatch(
                samples=[
                    PbTelemetrySample(
                        metric="cpu_pct", value=55.5, recorded_at_unix_ms=int(time.time() * 1000)
                    )
                ]
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    stmt = select(TelemetrySample).where(TelemetrySample.device_id == device.id)
    rows = (await db_session.execute(stmt)).scalars().all()
    assert len(rows) == 1
    assert rows[0].metric == "cpu_pct"
    assert rows[0].value == 55.5


async def test_fault_event_raises_fault_and_triggers_matching_alarm_rule(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    db_session.add(
        AlarmRule(
            tenant_id=tenant.id,
            name="critical",
            condition={"kind": "fault_code", "severity": "critical"},
        )
    )
    await db_session.commit()

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP",
                severity=FaultEvent.CRITICAL,
                message="cpu too hot",
                kind=FaultEvent.RAISED,
                at_unix_ms=int(time.time() * 1000),
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    faults = (
        await db_session.execute(select(Fault).where(Fault.device_id == device.id))
    ).scalars().all()
    assert len(faults) == 1
    assert faults[0].code == "OVERTEMP"

    alarms = (
        await db_session.execute(select(Alarm).where(Alarm.device_id == device.id))
    ).scalars().all()
    assert len(alarms) == 1
    assert alarms[0].source_fault_id == faults[0].id


async def test_fault_clear_sets_cleared_at_on_open_fault(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP",
                severity=FaultEvent.WARN,
                kind=FaultEvent.RAISED,
                at_unix_ms=1_700_000_000_000,
            )
        )
        yield AgentFrame(
            fault_event=FaultEvent(
                code="OVERTEMP", kind=FaultEvent.CLEARED, at_unix_ms=1_700_000_010_000
            )
        )

    async for _ in gateway_stub.Connect(frames()):
        pass

    fault = (
        await db_session.execute(select(Fault).where(Fault.device_id == device.id))
    ).scalar_one()
    assert fault.cleared_at is not None


async def test_log_upload_request_returns_signed_url_and_creates_bundle(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(heartbeat=_hb(str(device.id), credential))
        yield AgentFrame(
            log_upload_request=LogUploadRequest(
                kind=LogUploadRequest.LOG_BUNDLE,
                time_range_start_unix_ms=1_700_000_000_000,
                time_range_end_unix_ms=1_700_000_060_000,
                size_bytes_estimate=2048,
            )
        )

    saw_signed_url = False
    async for frame in gateway_stub.Connect(frames()):
        if frame.HasField("signed_upload_url"):
            saw_signed_url = True
            assert frame.signed_upload_url.upload_url

    assert saw_signed_url
    bundles = (
        await db_session.execute(select(LogBundle).where(LogBundle.device_id == device.id))
    ).scalars().all()
    assert len(bundles) == 1
    assert bundles[0].size_bytes == 2048
