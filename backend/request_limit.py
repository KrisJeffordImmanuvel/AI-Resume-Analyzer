"""Reject oversized requests early, before a huge upload is written to temporary disk space."""

import json

from fastapi import HTTPException


class _TooLarge(HTTPException):
    """Raised while reading the body. An HTTPException, so FastAPI's form reader passes it on as a 413."""

    def __init__(self, message: str):
        super().__init__(413, message)


class RequestSizeLimit:
    """ASGI middleware: requests larger than `max_bytes` get 413 with a plain message.

    Checks the declared Content-Length first, then counts the bytes actually received,
    so uploads without a length (chunked) are limited too.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    def _message(self) -> str:
        return (f"The upload is too large (over {self.max_bytes // (1024 * 1024)} MB in one request). "
                "Resumes can be up to 5 MB each.")

    async def _reject(self, send):
        body = json.dumps({"detail": self._message()}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope.get("headers", [])).get(b"content-length")
        if length is not None and length.isdigit() and int(length) > self.max_bytes:
            return await self._reject(send)

        received = 0
        started = False

        async def counting_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _TooLarge(self._message())
            return message

        async def tracking_send(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _TooLarge:
            if not started:
                await self._reject(send)
