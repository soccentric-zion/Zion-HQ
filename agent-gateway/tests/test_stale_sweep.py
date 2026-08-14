from datetime import datetime, timedelta, UTC

from app.models.device import Device
from app.models.enums import PairingState

from gateway.stale_sweep import sweep_once
from tests.factories import make_tenant


async def test_sweep_flips_stale_online_device_to_offline(db_session):
    tenant = await make_tenant(db_session)
    long_ago = datetime.now(UTC) - timedelta(hours=1)
    stale = Device(
        tenant_id=tenant.id,
        name="stale-device",
        pairing_state=PairingState.authorized,
        online=True,
        last_seen_at=long_ago,
    )
    fresh = Device(
        tenant_id=tenant.id,
        name="fresh-device",
        pairing_state=PairingState.authorized,
        online=True,
        last_seen_at=datetime.now(UTC),
    )
    db_session.add_all([stale, fresh])
    await db_session.commit()

    flipped = await sweep_once()
    assert flipped == 1

    await db_session.refresh(stale)
    await db_session.refresh(fresh)
    assert stale.online is False
    assert fresh.online is True


async def test_sweep_leaves_already_offline_devices_alone(db_session):
    tenant = await make_tenant(db_session)
    long_ago = datetime.now(UTC) - timedelta(hours=1)
    device = Device(
        tenant_id=tenant.id,
        name="already-offline",
        pairing_state=PairingState.authorized,
        online=False,
        last_seen_at=long_ago,
    )
    db_session.add(device)
    await db_session.commit()

    flipped = await sweep_once()
    assert flipped == 0
