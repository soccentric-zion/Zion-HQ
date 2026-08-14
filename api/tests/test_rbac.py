import pytest

from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_unauthenticated_request_is_401(client):
    resp = await client.get("/devices")
    assert resp.status_code == 401


async def test_me_returns_current_user(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin, email="me@example.com")
    await db_session.commit()
    login_as(client, admin)
    resp = await client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
    assert resp.json()["role"] == "admin"


@pytest.mark.parametrize("role", [UserRole.viewer, UserRole.operator, UserRole.admin])
async def test_all_roles_can_list_devices(client, db_session, role):
    tenant = await make_tenant(db_session)
    user = await make_user(db_session, tenant, role)
    await db_session.commit()
    login_as(client, user)
    resp = await client.get("/devices")
    assert resp.status_code == 200


async def test_viewer_cannot_create_device(client, db_session):
    tenant = await make_tenant(db_session)
    viewer = await make_user(db_session, tenant, UserRole.viewer)
    await db_session.commit()
    login_as(client, viewer)
    resp = await client.post("/devices", json={"name": "nope"})
    assert resp.status_code == 403


async def test_operator_can_create_device(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()
    login_as(client, operator)
    resp = await client.post("/devices", json={"name": "ok"})
    assert resp.status_code == 201


async def test_operator_cannot_invite_users(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()
    login_as(client, operator)
    resp = await client.post("/users/invite", json={"email": "new@example.com"})
    assert resp.status_code == 403


async def test_admin_can_invite_users(client, db_session):
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    await db_session.commit()
    login_as(client, admin)
    resp = await client.post("/users/invite", json={"email": "new@example.com", "role": "operator"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "operator"


async def test_operator_cannot_read_audit_log(client, db_session):
    tenant = await make_tenant(db_session)
    operator = await make_user(db_session, tenant, UserRole.operator)
    await db_session.commit()
    login_as(client, operator)
    resp = await client.get("/audit-log")
    assert resp.status_code == 403
