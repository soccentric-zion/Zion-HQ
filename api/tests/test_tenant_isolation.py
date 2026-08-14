from app.models.device import Device
from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_device_list_has_zero_cross_tenant_leakage(client, db_session):
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)
    admin_b = await make_user(db_session, tenant_b, UserRole.admin)

    db_session.add(Device(tenant_id=tenant_a.id, name="a-device"))
    db_session.add(Device(tenant_id=tenant_b.id, name="b-device"))
    await db_session.commit()

    login_as(client, admin_a)
    resp = await client.get("/devices")
    assert resp.status_code == 200
    names = {d["name"] for d in resp.json()["items"]}
    assert names == {"a-device"}

    login_as(client, admin_b)
    resp = await client.get("/devices")
    names = {d["name"] for d in resp.json()["items"]}
    assert names == {"b-device"}


async def test_device_detail_404s_for_other_tenants_device(client, db_session):
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)

    other_device = Device(tenant_id=tenant_b.id, name="not-yours")
    db_session.add(other_device)
    await db_session.commit()
    await db_session.refresh(other_device)

    login_as(client, admin_a)
    resp = await client.get(f"/devices/{other_device.id}")
    assert resp.status_code == 404


async def test_audit_log_isolated_per_tenant(client, db_session):
    tenant_a = await make_tenant(db_session)
    tenant_b = await make_tenant(db_session)
    admin_a = await make_user(db_session, tenant_a, UserRole.admin)
    admin_b = await make_user(db_session, tenant_b, UserRole.admin)
    await db_session.commit()

    login_as(client, admin_a)
    await client.post("/devices", json={"name": "device-a"})

    login_as(client, admin_b)
    resp = await client.get("/audit-log")
    assert resp.status_code == 200
    assert resp.json()["items"] == []
