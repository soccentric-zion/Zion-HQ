from app.models.device import Device
from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_create_device_returns_a_pairing_token(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    login_as(client, admin)
    resp = await client.post("/devices", json={"name": "unit-1"})
    assert resp.status_code == 201
    assert resp.json()["pairing_token"]


async def test_rotate_credential_issues_new_token_and_resets_to_pending(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()

    login_as(client, admin)
    created = (await client.post("/devices", json={"name": "unit-1"})).json()
    first_token = created["pairing_token"]
    device_id = created["device"]["id"]

    resp = await client.post(f"/devices/{device_id}/credential/rotate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pairing_token"] != first_token
    assert body["device"]["pairing_state"] == "pending"


async def test_operator_cannot_rotate_or_revoke_credentials(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    operator = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()

    login_as(client, admin)
    created = (await client.post("/devices", json={"name": "unit-1"})).json()
    device_id = created["device"]["id"]

    login_as(client, operator)
    assert (await client.post(f"/devices/{device_id}/credential/rotate")).status_code == 403
    assert (await client.post(f"/devices/{device_id}/credential/revoke")).status_code == 403


async def test_revoke_credential_marks_device_revoked(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="unit-1")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    login_as(client, admin)
    resp = await client.post(f"/devices/{device.id}/credential/revoke")
    assert resp.status_code == 200

    detail = await client.get(f"/devices/{device.id}")
    assert detail.json()["pairing_state"] == "revoked"
