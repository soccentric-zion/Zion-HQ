"""Device-side auth: pairing-token redemption and long-lived credential
validation. Mirrors the password/token discipline the REST API uses --
only hashes are ever stored or compared (app.services.credentials).
"""

from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.device_credential import DeviceCredential
from app.models.enums import CredentialKind, PairingState
from app.services.credentials import generate_token, hash_token


class PairingError(Exception):
    """Deliberately generic message for every failure mode (expired, used,
    unknown, wrong state) -- distinguishing them in the response would turn
    the pairing endpoint into a token-guessing oracle."""


async def redeem_pairing_token(session: AsyncSession, raw_token: str) -> tuple[Device, str]:
    token_hash = hash_token(raw_token)
    cred = (
        await session.execute(
            select(DeviceCredential).where(DeviceCredential.token_hash == token_hash)
        )
    ).scalar_one_or_none()

    now = datetime.now(UTC)
    if (
        cred is None
        or cred.kind != CredentialKind.pairing
        or cred.revoked_at is not None
        or cred.expires_at is None
        or cred.expires_at < now
    ):
        raise PairingError("invalid or expired pairing token")

    device = await session.get(Device, cred.device_id)
    if device is None or device.pairing_state != PairingState.pending:
        raise PairingError("device not in a pairable state")

    cred.revoked_at = now  # single-use: consume it immediately

    long_lived_raw = generate_token()
    session.add(
        DeviceCredential(
            device_id=device.id,
            kind=CredentialKind.long_lived,
            token_hash=hash_token(long_lived_raw),
        )
    )
    device.pairing_state = PairingState.authorized
    await session.flush()
    return device, long_lived_raw


async def validate_long_lived_credential(
    session: AsyncSession, device_id: str, raw_token: str
) -> Device | None:
    """Returns the Device if the credential is live and the device isn't
    disabled/revoked, else None. Checked on every frame by the caller, not
    just at connect -- disable must cut off an already-connected device too
    (ARCHITECTURE.md §5 / IMPLEMENTATION_PLAN §4.3)."""
    token_hash = hash_token(raw_token)
    cred = (
        await session.execute(
            select(DeviceCredential).where(
                DeviceCredential.device_id == device_id,
                DeviceCredential.token_hash == token_hash,
                DeviceCredential.kind == CredentialKind.long_lived,
                DeviceCredential.revoked_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if cred is None:
        return None

    device = await session.get(Device, device_id)
    if device is None or device.pairing_state in (PairingState.disabled, PairingState.revoked):
        return None
    return device
