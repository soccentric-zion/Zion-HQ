from datetime import datetime, UTC
from uuid import uuid4

from app.models.device import Device
from app.models.enums import UserRole
from tests.factories import login_as, make_tenant, make_user


async def test_post_then_get_sample_is_field_for_field_equal(client, db_session):
    """R3: POST a telemetry sample, then GET it back by id, and assert the
    returned fields equal the POSTed fields field-for-field AND match the
    POST response. The device must belong to the caller's tenant.
    """
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-lab-1")
    db_session.add(device)
    await db_session.commit()
    # The ORM `id` is populated after commit; refresh to be safe.
    await db_session.refresh(device)
    device_id = str(device.id)

    login_as(client, admin)

    recorded_at = datetime(2026, 7, 30, 12, 0, 5, tzinfo=UTC)
    posted = {
        "recorded_at": recorded_at.isoformat(),
        "metric": "cpu",
        "value": 73.5,
        "tags": {"core": "0", "source": "proc"},
    }

    resp = await client.post(f"/devices/{device_id}/telemetry", json=posted)
    assert resp.status_code == 201, resp.text
    created = resp.json()

    # The POST response must already reflect the POSTed fields (R3).
    # Compare as datetimes: the server may serialize +00:00 as Z.
    assert datetime.fromisoformat(created["recorded_at"].replace("Z", "+00:00")) == recorded_at
    assert created["metric"] == posted["metric"]
    assert created["value"] == posted["value"]
    assert created["tags"] == posted["tags"]
    assert created["device_id"] == device_id

    # GET the same sample back by id; it must equal the POST response field for
    # field -- the core R3 contract.
    sample_id = created["id"]
    get_resp = await client.get(f"/devices/{device_id}/telemetry/{sample_id}")
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()

    assert fetched == created, (
        "GET-by-id must return the same row the POST produced (R3 field-for-field)"
    )
    # Explicit field checks so a dict-equality quirk can't mask a divergence.
    assert fetched["id"] == created["id"]
    assert fetched["device_id"] == device_id
    assert datetime.fromisoformat(fetched["recorded_at"].replace("Z", "+00:00")) == recorded_at
    assert fetched["metric"] == posted["metric"]
    assert fetched["value"] == posted["value"]
    assert fetched["tags"] == posted["tags"]


async def test_get_sample_404_for_unknown_id(client, db_session):
    """A GET for a sample id that doesn't exist must 404, not leak existence."""
    tenant = await make_tenant(db_session)
    admin = await make_user(db_session, tenant, UserRole.admin)
    device = Device(tenant_id=tenant.id, name="pi-5-lab-2")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    login_as(client, admin)

    resp = await client.get(f"/devices/{device.id}/telemetry/{uuid4()}")
    assert resp.status_code == 404


async def test_operator_can_ingest_viewer_cannot(client, db_session):
    """require_role(operator) on POST: an operator may ingest, a viewer may not."""
    tenant = await make_tenant(db_session)
    op = await make_user(db_session, tenant, UserRole.operator)
    viewer = await make_user(db_session, tenant, UserRole.viewer)
    device = Device(tenant_id=tenant.id, name="pi-5-lab-3")
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)

    payload = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "metric": "ram",
        "value": 4096.0,
        "tags": {"unit": "MiB"},
    }

    login_as(client, op)
    resp = await client.post(f"/devices/{device.id}/telemetry", json=payload)
    assert resp.status_code == 201, resp.text

    login_as(client, viewer)
    resp = await client.post(f"/devices/{device.id}/telemetry", json=payload)
    assert resp.status_code == 403, resp.text


async def test_unauthenticated_post_returns_401(client):
    """A no-token (unauthenticated) POST to the mutating telemetry route must be
    rejected with 401 before any device/business logic runs. Mirrors the
    no-token pattern in test_rbac::test_unauthenticated_request_is_401.
    """
    resp = await client.post(
        f"/devices/{uuid4()}/telemetry",
        json={
            "recorded_at": datetime(2026, 7, 30, 12, 0, 5, tzinfo=UTC).isoformat(),
            "metric": "cpu",
            "value": 1.0,
            "tags": {},
        },
    )
    assert resp.status_code == 401, resp.text
