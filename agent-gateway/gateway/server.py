import asyncio
import logging

import grpc

from zionhq.agent_pb2_grpc import add_AgentLinkServicer_to_server

from gateway.config import get_gateway_settings
from gateway.servicer import AgentLinkServicer
from gateway.stale_sweep import run_forever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway.server")


async def serve() -> None:
    settings = get_gateway_settings()
    server = grpc.aio.server()
    add_AgentLinkServicer_to_server(AgentLinkServicer(), server)
    # Insecure for local dev only. Production must terminate TLS here (or at
    # a reverse proxy in front of it) -- the proto's own security notes
    # (ARCHITECTURE.md §3) assume devices dial in over TLS.
    server.add_insecure_port(f"[::]:{settings.grpc_port}")

    stop_event = asyncio.Event()
    sweep_task = asyncio.ensure_future(run_forever(stop_event))

    await server.start()
    logger.info("agent-gateway listening on :%d", settings.grpc_port)
    try:
        await server.wait_for_termination()
    finally:
        stop_event.set()
        sweep_task.cancel()


if __name__ == "__main__":
    asyncio.run(serve())
