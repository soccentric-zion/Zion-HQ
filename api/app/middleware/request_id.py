"""Request/correlation-id middleware.

Accepts or assigns a per-request id, binds it into the request logging
context, exposes it to route handlers as ``request.state.request_id``, and
echoes it back on the ``X-Request-ID`` response header so every log line for a
request shares one correlation id for tracing.
"""

import logging
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("zionhq.request")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _read_or_new_request_id(scope.get("headers", []))
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        logger.info(
            "%s %s request_id=%s",
            scope.get("method", ""),
            scope.get("path", ""),
            request_id,
        )

        await self.app(scope, receive, send_with_header)


def _read_or_new_request_id(headers) -> str:
    """Return the caller-supplied ``X-Request-ID`` or mint a fresh UUID."""
    for name, value in headers:
        if name.lower() == REQUEST_ID_HEADER.lower().encode("latin-1") and value:
            return value.decode("latin-1")
    return str(uuid.uuid4())
