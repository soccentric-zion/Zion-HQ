"""Near-real-time device online/offline push to the browser.

agent-gateway (a separate process) is the thing actually flipping
`device.online` in Postgres as devices connect/disconnect. Rather than a
cross-process pub/sub (Postgres LISTEN/NOTIFY, Redis), this API process
runs a short-interval poll-and-diff loop per tenant with at least one
subscribed WebSocket and only pushes rows whose (online, last_seen_at)
changed since the last poll -- simple, and "near-real-time" (a few seconds
of lag) is what IMPLEMENTATION_PLAN §2.4 actually asks for, not sub-second.
"""

import asyncio
import logging
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select

from app.db.base import get_session_factory
from app.models.device import Device

logger = logging.getLogger("device_status_broadcast")

POLL_INTERVAL_S = 2.0


class TenantSubscribers:
    def __init__(self) -> None:
        self._sockets: dict[UUID, set[WebSocket]] = {}
        self._last_snapshot: dict[UUID, dict[UUID, tuple[bool, str | None]]] = {}

    def subscribe(self, tenant_id: UUID, ws: WebSocket) -> None:
        self._sockets.setdefault(tenant_id, set()).add(ws)

    def unsubscribe(self, tenant_id: UUID, ws: WebSocket) -> None:
        sockets = self._sockets.get(tenant_id)
        if sockets:
            sockets.discard(ws)
            if not sockets:
                self._sockets.pop(tenant_id, None)
                self._last_snapshot.pop(tenant_id, None)

    def tenants_with_subscribers(self) -> list[UUID]:
        return list(self._sockets.keys())

    async def broadcast(self, tenant_id: UUID, payload: dict) -> None:
        for ws in list(self._sockets.get(tenant_id, ())):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 - a dead socket shouldn't kill the poll loop
                self.unsubscribe(tenant_id, ws)

    def diff_and_update(
        self, tenant_id: UUID, current: dict[UUID, tuple[bool, str | None]]
    ) -> dict[UUID, tuple[bool, str | None]]:
        previous = self._last_snapshot.get(tenant_id, {})
        changed = {
            device_id: state
            for device_id, state in current.items()
            if previous.get(device_id) != state
        }
        self._last_snapshot[tenant_id] = current
        return changed


subscribers = TenantSubscribers()


async def poll_loop(stop_event: asyncio.Event | None = None) -> None:
    session_factory = get_session_factory()
    while stop_event is None or not stop_event.is_set():
        for tenant_id in subscribers.tenants_with_subscribers():
            try:
                async with session_factory() as session:
                    rows = (
                        await session.execute(
                            select(Device.id, Device.online, Device.last_seen_at).where(
                                Device.tenant_id == tenant_id
                            )
                        )
                    ).all()
                current = {
                    row.id: (row.online, row.last_seen_at.isoformat() if row.last_seen_at else None)
                    for row in rows
                }
                changed = subscribers.diff_and_update(tenant_id, current)
                for device_id, (online, last_seen_at) in changed.items():
                    payload = {
                        "device_id": str(device_id),
                        "online": online,
                        "last_seen_at": last_seen_at,
                    }
                    await subscribers.broadcast(tenant_id, payload)
            except Exception:
                logger.exception("device status poll failed for tenant %s", tenant_id)
        await asyncio.sleep(POLL_INTERVAL_S)
