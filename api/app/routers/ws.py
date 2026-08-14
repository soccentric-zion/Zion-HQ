from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.deps import SESSION_COOKIE_NAME
from app.auth.session import InvalidSession, verify_session_token
from app.services.device_status_broadcast import subscribers

router = APIRouter(tags=["ws"])


@router.websocket("/ws/devices")
async def ws_devices(websocket: WebSocket) -> None:
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        await websocket.close(code=4401)
        return
    try:
        claims = verify_session_token(token)
    except InvalidSession:
        await websocket.close(code=4401)
        return

    tenant_id = UUID(claims["tenant_id"])
    await websocket.accept()
    subscribers.subscribe(tenant_id, websocket)
    try:
        while True:
            # No client->server messages expected; just keep the socket open
            # and detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        subscribers.unsubscribe(tenant_id, websocket)
