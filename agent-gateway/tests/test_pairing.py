import time

import grpc
import pytest

from app.models.enums import PairingState
from zionhq.agent_pb2 import AgentFrame, Heartbeat, PairingHandshake
from tests.factories import (
    make_authorized_device_with_credential,
    make_pending_device_with_pairing_token,
    make_tenant,
)


async def _pair(stub, token: str):
    async def frames():
        yield AgentFrame(pairing_handshake=PairingHandshake(pairing_token=token))

    async for frame in stub.Connect(frames()):
        return frame
    return None


async def test_valid_pairing_token_issues_credential_and_authorizes_device(
    gateway_stub, db_session
):
    tenant = await make_tenant(db_session)
    device, token = await make_pending_device_with_pairing_token(db_session, tenant)

    response = await _pair(gateway_stub, token)

    assert response.pairing_result.success is True
    assert response.pairing_result.device_id == str(device.id)
    assert response.pairing_result.credential_token

    await db_session.refresh(device)
    assert device.pairing_state == PairingState.authorized


async def test_invalid_pairing_token_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    await make_pending_device_with_pairing_token(db_session, tenant)

    response = await _pair(gateway_stub, "not-a-real-token")

    assert response.pairing_result.success is False


async def test_expired_pairing_token_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, token = await make_pending_device_with_pairing_token(db_session, tenant, expired=True)

    response = await _pair(gateway_stub, token)

    assert response.pairing_result.success is False
    await db_session.refresh(device)
    assert device.pairing_state == PairingState.pending


async def test_pairing_token_is_single_use(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    _, token = await make_pending_device_with_pairing_token(db_session, tenant)

    first = await _pair(gateway_stub, token)
    assert first.pairing_result.success is True

    second = await _pair(gateway_stub, token)
    assert second.pairing_result.success is False


async def test_heartbeat_with_valid_credential_marks_device_online(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
                agent_version="test",
            )
        )

    got_ack = False
    async for frame in gateway_stub.Connect(frames()):
        if frame.HasField("heartbeat_ack"):
            got_ack = True

    assert got_ack
    await db_session.refresh(device)
    assert device.online is True
    assert device.last_seen_at is not None


async def test_heartbeat_with_invalid_credential_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, _real_credential = await make_authorized_device_with_credential(db_session, tenant)

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token="wrong-token",
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED


async def test_disabled_device_heartbeat_is_rejected(gateway_stub, db_session):
    tenant = await make_tenant(db_session)
    device, credential = await make_authorized_device_with_credential(db_session, tenant)
    device.pairing_state = PairingState.disabled
    await db_session.commit()

    async def frames():
        yield AgentFrame(
            heartbeat=Heartbeat(
                device_id=str(device.id),
                credential_token=credential,
                sent_at_unix_ms=int(time.time() * 1000),
            )
        )

    with pytest.raises(grpc.aio.AioRpcError) as exc_info:
        async for _ in gateway_stub.Connect(frames()):
            pass
    assert exc_info.value.code() == grpc.StatusCode.UNAUTHENTICATED
