"""In-memory device_id -> outbound-frame-queue map.

Single-instance only for now -- IMPLEMENTATION_PLAN §2.1 notes this becomes
Redis-backed if the gateway is horizontally scaled (a command pushed to a
device connected to a *different* gateway replica wouldn't reach it
otherwise). Not needed until there's more than one gateway replica.
"""

import asyncio


class ConnectionManager:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def register(self, device_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[device_id] = queue
        return queue

    def unregister(self, device_id: str) -> None:
        self._queues.pop(device_id, None)

    def is_connected(self, device_id: str) -> bool:
        return device_id in self._queues

    async def push(self, device_id: str, frame) -> bool:
        queue = self._queues.get(device_id)
        if queue is None:
            return False
        await queue.put(frame)
        return True

    def connected_device_ids(self) -> list[str]:
        return list(self._queues.keys())


manager = ConnectionManager()
