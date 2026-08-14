"""Scripted stand-in for a real Zion-Configuration HQ agent -- speaks the
zionhq.agent proto so agent-gateway's Phase 2+ work can be built and
tested without waiting on Configuration's own outbound-agent implementation
(IMPLEMENTATION_PLAN §2.3).

Usage:
    python -m test_client.client pair <gateway_host:port> <pairing_token>
    python -m test_client.client heartbeat <gateway_host:port> <device_id> <credential_token>
"""

import asyncio
import sys
import time

import grpc

from zionhq.agent_pb2 import AgentFrame, Heartbeat, PairingHandshake


async def pair(target: str, pairing_token: str) -> None:
    from zionhq.agent_pb2_grpc import AgentLinkStub

    async with grpc.aio.insecure_channel(target) as channel:
        stub = AgentLinkStub(channel)

        async def frames():
            yield AgentFrame(pairing_handshake=PairingHandshake(pairing_token=pairing_token))

        async for server_frame in stub.Connect(frames()):
            if server_frame.HasField("pairing_result"):
                result = server_frame.pairing_result
                if result.success:
                    print(f"device_id={result.device_id}")
                    print(f"credential_token={result.credential_token}")
                else:
                    print(f"pairing failed: {result.error}", file=sys.stderr)
                    sys.exit(1)
                return


async def heartbeat_loop(
    target: str, device_id: str, credential_token: str, count: int = 3
) -> None:
    from zionhq.agent_pb2_grpc import AgentLinkStub

    async with grpc.aio.insecure_channel(target) as channel:
        stub = AgentLinkStub(channel)

        async def frames():
            for _ in range(count):
                yield AgentFrame(
                    heartbeat=Heartbeat(
                        device_id=device_id,
                        credential_token=credential_token,
                        sent_at_unix_ms=int(time.time() * 1000),
                        agent_version="test-client-0.1",
                    )
                )
                await asyncio.sleep(1)

        async for server_frame in stub.Connect(frames()):
            if server_frame.HasField("heartbeat_ack"):
                print(f"heartbeat_ack server_time={server_frame.heartbeat_ack.server_time_unix_ms}")


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    command, target, *rest = sys.argv[1:]
    if command == "pair":
        asyncio.run(pair(target, rest[0]))
    elif command == "heartbeat":
        asyncio.run(heartbeat_loop(target, rest[0], rest[1]))
    else:
        print(f"unknown command {command}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
