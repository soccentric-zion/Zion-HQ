from datetime import datetime, UTC
from uuid import uuid4

from app.models.device import Device
from app.models.enums import AlarmState, UserRole
from tests.factories import login_as, make_tenant, make_user


# Byte order of the 4-byte alarm code (must match the router's decoder and
# the daemon's encoder): big-endian uint32 where
#   byte 0 (MSB) = major_id, byte 1 = sub_section,
#   byte 2       = fault_type, byte 3 (LSB) = severity.
# 0x01020304 -> major_id=1, sub_section=2, fault_type=3, severity=4.
#
# These tests exercise the device-reported ``alarms`` table (model
# DeviceAlarm, __tablename__ == "alarms"), which is distinct from the
# rule-based ``alarm`` table.


async def test_post_alarm_then_get_decodes_4_fields(client, db_session):
    """R3: POST a device-reported 4-byte alarm, then GET the device alarms
    list and assert the returned row decodes all 4 fields correctly and
    alarm_code round-trips.
    """
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-alarm-1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    device_id = str(device.id)

    login_as(client, admin)

    triggered_at = datetime(2026, 7, 30, 12, 0, 5, tzinfo=UTC)
    posted = {
        "alarm_code": "0x01020304",
        "triggered_at": triggered_at.isoformat(),
    }

    resp = await client.post(f"/devices/{device_id}/alarms", json=posted)
    assert resp.status_code == 201, resp.text
    created = resp.json()

    # The POST response must already reflect the decoded 4 fields (R3).
    assert created["major_id"] == 1
    assert created["sub_section"] == 2
    assert created["fault_type"] == 3
    assert created["severity"] == 4
    assert created["alarm_code"] == 0x01020304
    assert created["state"] == AlarmState.active.value
    assert created["device_id"] == device_id
    assert "alarm_rule_id" not in created  # DeviceAlarm has no rule

    # GET the device alarms list; the row must carry the same decoded fields.
    list_resp = await client.get(f"/devices/{device_id}/alarms")
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["items"]
    assert len(items) == 1
    fetched = items[0]

    assert fetched["id"] == created["id"]
    assert fetched["major_id"] == 1
    assert fetched["sub_section"] == 2
    assert fetched["fault_type"] == 3
    assert fetched["severity"] == 4
    assert fetched["alarm_code"] == 0x01020304
    assert fetched["device_id"] == device_id


async def test_post_alarm_boundary_values(client, db_session):
    """All-zero and all-0xFF bytes round-trip through the 4-byte decode,
    including the 0xFFFFFFFF boundary that overflows int32 (D1: BigInteger).
    """
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-alarm-bnd")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    device_id = str(device.id)

    login_as(client, admin)

    for code_hex, expected in [
        ("0x00000000", (0, 0, 0, 0)),
        ("0xffffffff", (0xFF, 0xFF, 0xFF, 0xFF)),
        ("0xff00ff00", (0xFF, 0x00, 0xFF, 0x00)),
    ]:
        resp = await client.post(
            f"/devices/{device_id}/alarms",
            json={
                "alarm_code": code_hex,
                "triggered_at": datetime.now(UTC).isoformat(),
            },
        )
        assert resp.status_code == 201, (code_hex, resp.text)
        body = resp.json()
        decoded = (body["major_id"], body["sub_section"], body["fault_type"], body["severity"])
        assert decoded == expected
        assert body["alarm_code"] == int(code_hex, 16)


async def test_cross_tenant_device_404(client, db_session):
    """A tenant cannot ingest alarms against another tenant's device (404)."""
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)
    device_b = Device(tenant_id=tenant_b.id, name="pi-5-other-tenant")
    db_session.add(device_b)
    await db_session.commit()
    await db_session.refresh(device_b)

    login_as(client, admin_a)
    resp = await client.post(
        f"/devices/{device_b.id}/alarms",
        json={
            "alarm_code": "0x01020304",
            "triggered_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 404, resp.text


async def test_clear_device_alarm_resolves(client, db_session):
    """R3: the device-scoped `clear` verb resolves the alarm (state=resolved).
    `clear` == `resolve` -- there is no separate `cleared` state (F5).
    """
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-alarm-clear")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    device_id = str(device.id)

    login_as(client, admin)

    posted = await client.post(
        f"/devices/{device_id}/alarms",
        json={
            "alarm_code": "0x01020304",
            "triggered_at": datetime.now(UTC).isoformat(),
        },
    )
    assert posted.status_code == 201, posted.text
    alarm_id = posted.json()["id"]

    clear = await client.post(f"/devices/{device_id}/alarms/{alarm_id}/clear")
    assert clear.status_code == 200, clear.text
    cleared = clear.json()
    assert cleared["state"] == AlarmState.resolved.value
    assert cleared["resolved_at"] is not None


async def test_operator_can_ingest_viewer_cannot(client, db_session):
    """require_role(operator) on POST ingest: an operator may ingest, a viewer may not."""
    tenant = await make_tenant(db_session)
    op = await make_user(db_session, tenant, UserRole.operator)
    viewer = await make_user(db_session, tenant, UserRole.viewer)
    device = Device(tenant_id=tenant.id, name="pi-5-alarm-rbac")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = {
        "alarm_code": "0x01020304",
        "triggered_at": datetime.now(UTC).isoformat(),
    }

    login_as(client, op)
    resp = await client.post(f"/devices/{device.id}/alarms", json=payload)
    assert resp.status_code == 201, resp.text

    login_as(client, viewer)
    resp = await client.post(f"/devices/{device.id}/alarms", json=payload)
    assert resp.status_code == 403, resp.text


async def test_clear_unknown_alarm_404(client, db_session):
    """Clearing a non-existent alarm on a real device 404s, not leaks existence."""
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-alarm-404")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    login_as(client, admin)
    resp = await client.post(f"/devices/{device.id}/alarms/{uuid4()}/clear")
    assert resp.status_code == 404, resp.text
