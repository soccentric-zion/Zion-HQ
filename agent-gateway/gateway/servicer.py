"""gRPC glue: AgentLink.Connect bidi stream. Business logic per frame type
lives in handlers.py; this module owns connection lifecycle, auth, and
dispatch.

Auth model: only PairingHandshake and Heartbeat frames carry a credential
token (see proto/zionhq/agent.proto) -- there's no per-frame token on
TelemetryBatch/FaultEvent/etc. So the full token comparison happens once at
connect and again on every Heartbeat (which the device sends periodically
throughout the connection); between heartbeats, every inbound frame still
re-checks the device's live `pairing_state` (cheap, no hashing) so a
disable/revoke takes effect within one heartbeat interval rather than only
at the next reconnect -- this is the practical reading of
IMPLEMENTATION_PLAN §2.2's "checked on each frame."
"""

import asyncio
import logging
from datetime import datetime, UTC

import grpc

from app.db.base import get_session_factory
from app.models.device import Device
from app.models.enums import PairingState
from zionhq.agent_pb2 import HeartbeatAck, PairingResult, ServerFrame, SignedUploadUrl
from zionhq.agent_pb2_grpc import AgentLinkServicer as _AgentLinkServicer

from gateway import handlers
from gateway.auth import PairingError, redeem_pairing_token, validate_long_lived_credential
from gateway.config import get_gateway_settings
from gateway.connection_manager import manager

logger = logging.getLogger("gateway.servicer")


class AgentLinkServicer(_AgentLinkServicer):
    async def Connect(self, request_iterator, context):
        session_factory = get_session_factory()

        first = await _anext_or_none(request_iterator)
        if first is None:
            return

        if first.HasField("pairing_handshake"):
            token = first.pairing_handshake.pairing_token
            async with session_factory() as session:
                async for out in self._handle_pairing(session, token):
                    yield out
            return  # device reconnects with a Heartbeat using its new credential

        if not first.HasField("heartbeat"):
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "first frame must be pairing_handshake or heartbeat",
            )
            return

        device_id = first.heartbeat.device_id
        async with session_factory() as session:
            device = await validate_long_lived_credential(
                session, device_id, first.heartbeat.credential_token
            )
            if device is None:
                await context.abort(
                    grpc.StatusCode.UNAUTHENTICATED, "invalid credential or device disabled"
                )
                return
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            await session.commit()

        settings = get_gateway_settings()
        queue = manager.register(device_id)
        try:
            yield ServerFrame(
                heartbeat_ack=HeartbeatAck(
                    server_time_unix_ms=_now_ms(),
                    next_heartbeat_interval_s=settings.sweep_interval_s,
                )
            )
            async for out in self._pump(request_iterator, queue, device_id, session_factory):
                yield out
        finally:
            manager.unregister(device_id)

    async def _pump(self, request_iterator, queue, device_id, session_factory):
        """Interleave inbound device frames with outbound queued commands."""
        inbound_task = asyncio.ensure_future(_anext_or_none(request_iterator))
        outbound_task = asyncio.ensure_future(queue.get())
        try:
            while True:
                done, _ = await asyncio.wait(
                    {inbound_task, outbound_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if inbound_task in done:
                    frame = inbound_task.result()
                    if frame is None:
                        return
                    async with session_factory() as session:
                        still_allowed = await self._reauth(session, device_id, frame)
                        if not still_allowed:
                            return
                        response = await self._dispatch(session, device_id, frame)
                        await session.commit()
                    if response is not None:
                        yield response
                    inbound_task = asyncio.ensure_future(_anext_or_none(request_iterator))
                if outbound_task in done:
                    yield outbound_task.result()
                    outbound_task = asyncio.ensure_future(queue.get())
        finally:
            inbound_task.cancel()
            outbound_task.cancel()

    async def _reauth(self, session, device_id: str, frame) -> bool:
        if frame.HasField("heartbeat"):
            device = await validate_long_lived_credential(
                session, device_id, frame.heartbeat.credential_token
            )
            return device is not None
        # Non-heartbeat frames carry no token; cheaply confirm the device
        # hasn't been disabled/revoked mid-connection.

        device = await session.get(Device, device_id)
        return device is not None and device.pairing_state not in (
            PairingState.disabled,
            PairingState.revoked,
        )

    async def _dispatch(self, session, device_id: str, frame) -> ServerFrame | None:

        device = await session.get(Device, device_id)
        if device is None:
            return None

        if frame.HasField("heartbeat"):
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            return None
        if frame.HasField("telemetry_batch"):
            device.online = True
            device.last_seen_at = datetime.now(UTC)
            await handlers.handle_telemetry_batch(session, device, frame.telemetry_batch)
            return None
        if frame.HasField("fault_event"):
            await handlers.handle_fault_event(session, device, frame.fault_event)
            return None
        if frame.HasField("log_upload_request"):
            request_ref, url, expires_in = await handlers.handle_log_upload_request(
                session, device, frame.log_upload_request
            )
            return ServerFrame(
                signed_upload_url=SignedUploadUrl(
                    request_ref=request_ref,
                    upload_url=url,
                    expires_at_unix_ms=_now_ms() + expires_in * 1000,
                )
            )
        if frame.HasField("command_ack"):
            ack = frame.command_ack
            await handlers.handle_command_ack(
                session, device, ack.command_id, ack.success, ack.error
            )
            return None
        return None

    async def _handle_pairing(self, session, raw_token: str):
        try:
            device, long_lived = await redeem_pairing_token(session, raw_token)
            await session.commit()
        except PairingError as exc:
            yield ServerFrame(pairing_result=PairingResult(success=False, error=str(exc)))
            return
        yield ServerFrame(
            pairing_result=PairingResult(
                success=True, device_id=str(device.id), credential_token=long_lived
            )
        )


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


async def _anext_or_none(iterator):
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        return None
