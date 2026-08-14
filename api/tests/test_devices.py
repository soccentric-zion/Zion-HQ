from datetime import datetime, timedelta, UTC

from app.models.device import Device
from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_device_list_sorted_online_then_recent_then_name(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    now = datetime.now(UTC)

    day_ago = now - timedelta(days=1)
    minute_ago = now - timedelta(minutes=1)
    db_session.add_all(
        [
            Device(tenant_id=tenant.id, name="offline-old", online=False, last_seen_at=day_ago),
            Device(tenant_id=tenant.id, name="online-b", online=True, last_seen_at=minute_ago),
            Device(tenant_id=tenant.id, name="online-a", online=True, last_seen_at=now),
        ]
    )
    await db_session.commit()

    login_as(client, admin)
    resp = await client.get("/devices")
    assert resp.status_code == 200
    names = [d["name"] for d in resp.json()["items"]]
    assert names == ["online-a", "online-b", "offline-old"]


async def test_create_device_writes_audit_log(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    login_as(client, admin)
    resp = await client.post("/devices", json={"name": "unit-1"})
    assert resp.status_code == 201
    assert resp.json()["device"]["pairing_state"] == "pending"

    audit_resp = await client.get("/audit-log")
    actions = [row["action"] for row in audit_resp.json()["items"]]
    assert "device.create" in actions


async def test_device_name_search(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    db_session.add_all(
        [
            Device(tenant_id=tenant.id, name="jetson-lab-1"),
            Device(tenant_id=tenant.id, name="jetson-lab-2"),
            Device(tenant_id=tenant.id, name="other"),
        ]
    )
    await db_session.commit()

    login_as(client, admin)
    resp = await client.get("/devices", params={"q": "jetson"})
    names = {d["name"] for d in resp.json()["items"]}
    assert names == {"jetson-lab-1", "jetson-lab-2"}
