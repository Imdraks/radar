"""Bound total request bodies, including chunked/multipart uploads before parsing."""

from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes=52 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", []))
        length = headers.get(b"content-length")
        if length:
            try:
                amount = int(length)
                if amount < 0:
                    raise ValueError()
            except ValueError:
                return await JSONResponse(
                    {"detail": "Taille de requête invalide."}, 400
                )(scope, receive, send)
            if amount > self.max_bytes:
                return await JSONResponse({"detail": "Requête trop volumineuse."}, 413)(
                    scope, receive, send
                )
        size = 0
        started = False

        async def bounded():
            nonlocal size
            message = await receive()
            if message["type"] == "http.request":
                size += len(message.get("body", b""))
                if size > self.max_bytes:
                    raise HTTPException(413, "Requête trop volumineuse.")
            return message

        async def observed(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, bounded, observed)
        except HTTPException as error:
            if error.status_code != 413 or started:
                raise
            await JSONResponse({"detail": "Requête trop volumineuse."}, 413)(
                scope, receive, send
            )
