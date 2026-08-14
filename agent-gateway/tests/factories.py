from datetime import datetime, timedelta, UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.device_credential import DeviceCredential
from app.models.enums import CredentialKind, PairingState
from app.models.tenant import Tenant
from app.services.credentials import generate_token, hash_token


async def make_tenant(session: AsyncSession) -> Tenant:
    tenant = Tenant(name="gateway-test-tenant")
    session.add(tenant)
    await session.flush()
    return tenant


async def make_pending_device_with_pairing_token(
    session: AsyncSession, tenant: Tenant, *, expired: bool = False
) -> tuple[Device, str]:
    device = Device(tenant_id=tenant.id, name="test-device", pairing_state=PairingState.pending)
    session.add(device)
    await session.flush()

    raw_token = generate_token()
    now = datetime.now(UTC)
    expires_at = now - timedelta(seconds=1) if expired else now + timedelta(minutes=15)
    session.add(
        DeviceCredential(
            device_id=device.id,
            kind=CredentialKind.pairing,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
    )
    await session.commit()
    return device, raw_token


async def make_authorized_device_with_credential(
    session: AsyncSession, tenant: Tenant
) -> tuple[Device, str]:
    device = Device(
        tenant_id=tenant.id, name="paired-device", pairing_state=PairingState.authorized
    )
    session.add(device)
    await session.flush()

    raw_token = generate_token()
    session.add(
        DeviceCredential(
            device_id=device.id, kind=CredentialKind.long_lived, token_hash=hash_token(raw_token)
        )
    )
    await session.commit()
    return device, raw_token
