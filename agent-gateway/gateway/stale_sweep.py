"""Backstop for hard power-loss disconnects: no clean disconnect frame ever
arrives, so presence has to be inferred from a heartbeat-recency deadline
(IMPLEMENTATION_PLAN §2.1 / ARCHITECTURE.md §3 step 5).
"""

import asyncio
import logging
from datetime import datetime, timedelta, UTC

from sqlalchemy import update

from app.config import get_settings
from app.db.base import get_session_factory
from app.models.device import Device

from gateway.config import get_gateway_settings

logger = logging.getLogger("gateway.stale_sweep")


async def sweep_once() -> int:
    settings = get_settings()
    deadline = datetime.now(UTC) - timedelta(
        seconds=settings.heartbeat_interval_s * settings.heartbeat_missed_threshold
    )
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            update(Device)
            .where(Device.online.is_(True), Device.last_seen_at < deadline)
            .values(online=False)
        )
        await session.commit()
        return result.rowcount or 0


async def run_forever(stop_event: asyncio.Event | None = None) -> None:
    gw_settings = get_gateway_settings()
    while stop_event is None or not stop_event.is_set():
        try:
            flipped = await sweep_once()
            if flipped:
                logger.info("stale sweep: marked %d device(s) offline", flipped)
        except Exception:
            logger.exception("stale sweep iteration failed")
        await asyncio.sleep(gw_settings.sweep_interval_s)
