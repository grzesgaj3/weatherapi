"""Globalne handlery wyjątków – ujednolicony envelope błędów."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import error_response

logger = logging.getLogger("weatherapi")

# 422: nazwa stałej zmieniła się w nowszych wersjach Starlette.
UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


def _normalize_detail(detail) -> dict:
    """Jeśli w detail jest już nasz envelope – użyj go; inaczej opakuj."""
    if isinstance(detail, dict) and "error" in detail:
        return detail
    return error_response("http_error", str(detail))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_normalize_detail(exc.detail),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err["loc"][1:]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=UNPROCESSABLE,
            content=error_response("validation_error", "Błąd walidacji danych", details),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_response(
                "rate_limited", "Zbyt wiele żądań – spróbuj ponownie później"
            ),
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Logujemy szczegóły po stronie serwera, klientowi nie ujawniamy wnętrza.
        logger.exception("Nieobsłużony wyjątek na %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response("internal_error", "Wewnętrzny błąd serwera"),
        )
