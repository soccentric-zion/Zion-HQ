import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.middleware.request_id import RequestIDMiddleware
from app.routers import alarms, audit_log, auth, devices, faults, logs, telemetry, users, ws
from app.services.device_status_broadcast import poll_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    poll_task = asyncio.ensure_future(poll_loop(stop_event))
    yield
    stop_event.set()
    poll_task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Zion-HQ API", version="0.1.0", lifespan=lifespan)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # Structured request/correlation-id logging: accept or mint X-Request-ID,
    # expose it as request.state.request_id, log each request with it, and
    # echo it back on the response header.
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(devices.router)
    app.include_router(users.router)
    app.include_router(audit_log.router)
    app.include_router(telemetry.router)
    app.include_router(faults.router)
    app.include_router(alarms.device_alarms_router)
    app.include_router(alarms.alarms_router)
    app.include_router(alarms.alarm_rules_router)
    app.include_router(logs.router)
    app.include_router(ws.router)

    @app.get("/healthz", tags=["meta"])
    async def healthz():
        return {"status": "ok"}

    return app


app = create_app()
