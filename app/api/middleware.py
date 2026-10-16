"""Middleware: limit rozmiaru ciała żądania."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.schemas.common import error_response


class BodySizeLimitMiddleware:
    """Odrzuca żądania z ciałem większym niż `max_bytes` (HTTP 413).

    Najpierw sprawdza nagłówek Content-Length (szybka ścieżka), a jeśli go
    brak – buforuje ciało, przerywając po przekroczeniu limitu.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    def _too_large(self) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content=error_response(
                "payload_too_large",
                f"Ciało żądania przekracza {self.max_bytes} bajtów",
            ),
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > self.max_bytes:
                await self._too_large()(scope, receive, send)
                return

        # Buforujemy ciało, aby móc odrzucić zbyt duże strumienie bez
        # naruszenia kontraktu ASGI (jedna odpowiedź na żądanie).
        received = 0
        parts: list[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                break
            parts.append(message.get("body", b""))
            received += len(message.get("body", b""))
            if received > self.max_bytes:
                await self._too_large()(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        body = b"".join(parts)
        replayed = False

        async def replay_receive() -> Message:
            nonlocal replayed
            if replayed:
                return {"type": "http.disconnect"}
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, replay_receive, send)
