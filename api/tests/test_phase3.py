from datetime import datetime, timedelta, UTC

from app.models.alarm import Alarm, AlarmRule
from app.models.device import Device
from app.models.enums import AlarmState, FaultSeverity, UserRole
from app.models.fault import Fault
from app.models.log_bundle import LogBundle
from app.models.telemetry import TelemetrySample
from tests.factories import login_as, make_tenant, make_user


async def _device(db_session, tenant):
    device = Device(tenant_id=tenant.id, name="d1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


async def test_telemetry_groups_by_metric_and_excludes_location(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = await _device(db_session, tenant)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            TelemetrySample(device_id=device.id, recorded_at=now, metric="cpu_pct", value=42.0),
            TelemetrySample(
                device_id=device.id,
                recorded_at=now - timedelta(minutes=1),
                metric="cpu_pct",
                value=40.0,
            ),
            TelemetrySample(
                device_id=device.id,
                recorded_at=now,
                metric="location",
                value=0.0,
                tags={"lat": "1"},
            ),
        ]
    )
    await db_session.commit()

    login_as(client, admin)
    resp = await client.get(f"/devices/{device.id}/telemetry")
    assert resp.status_code == 200
    body = resp.json()
    assert "location" not in body
    assert [p["value"] for p in body["cpu_pct"]] == [40.0, 42.0]  # oldest -> newest


async def test_telemetry_404s_for_other_tenants_device(client, db_session):
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)
    device_b = await _device(db_session, tenant_b)

    login_as(client, admin_a)
    resp = await client.get(f"/devices/{device_b.id}/telemetry")
    assert resp.status_code == 404


async def test_fault_feed_newest_first(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = await _device(db_session, tenant)
    now = datetime.now(UTC)
    db_session.add_all(
        [
            Fault(
                device_id=device.id,
                code="OLD",
                severity=FaultSeverity.info,
                raised_at=now - timedelta(hours=1),
            ),
            Fault(device_id=device.id, code="NEW", severity=FaultSeverity.critical, raised_at=now),
        ]
    )
    await db_session.commit()

    login_as(client, admin)
    resp = await client.get(f"/devices/{device.id}/faults")
    codes = [f["code"] for f in resp.json()["items"]]
    assert codes == ["NEW", "OLD"]


async def test_alarm_rule_create_and_list_is_tenant_scoped(client, db_session):
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)
    admin_b = await make_user(db_session, tenant_b, UserRole.admin)
    await db_session.commit()

    login_as(client, admin_a)
    condition = {"kind": "fault_code", "severity": "critical"}
    body = {"name": "critical-faults", "condition": condition}
    resp = await client.post("/alarm-rules", json=body)
    assert resp.status_code == 201

    login_as(client, admin_b)
    resp = await client.get("/alarm-rules")
    assert resp.json() == []


async def test_acknowledge_and_resolve_alarm(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = await _device(db_session, tenant)
    rule = AlarmRule(tenant_id=tenant.id, name="r", condition={"kind": "fault_code"})
    db_session.add(rule)
    await db_session.flush()
    alarm = Alarm(
        alarm_rule_id=rule.id,
        device_id=device.id,
        state=AlarmState.active,
        triggered_at=datetime.now(UTC),
    )
    db_session.add(alarm)
    await db_session.commit()
    await db_session.refresh(alarm)

    login_as(client, admin)
    resp = await client.post(f"/alarms/{alarm.id}/acknowledge")
    assert resp.status_code == 200
    assert resp.json()["state"] == "acknowledged"

    resp = await client.post(f"/alarms/{alarm.id}/resolve")
    assert resp.status_code == 200
    assert resp.json()["state"] == "resolved"


async def test_log_bundle_list_and_download_url(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = await _device(db_session, tenant)
    now = datetime.now(UTC)
    bundle = LogBundle(
        device_id=device.id,
        storage_url="log_bundle/x/y",
        size_bytes=1024,
        uploaded_at=now,
        time_range_start=now - timedelta(hours=1),
        time_range_end=now,
    )
    db_session.add(bundle)
    await db_session.commit()
    await db_session.refresh(bundle)

    login_as(client, admin)
    resp = await client.get(f"/devices/{device.id}/logs")
    assert len(resp.json()["items"]) == 1

    resp = await client.get(f"/devices/{device.id}/logs/{bundle.id}/download")
    assert resp.status_code == 200
    assert resp.json()["download_url"]
