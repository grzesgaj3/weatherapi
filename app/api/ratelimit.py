"""Rate limiting per stacja/klient (slowapi)."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings
from app.services.security import hash_api_key


def rate_limit_key(request: Request) -> str:
    """Klucz limitu: hash klucza urządzenia/admina albo adres IP klienta.

    Nie przechowujemy surowych kluczy – tylko ich hash.
    """
    key = request.headers.get("X-API-Key") or request.headers.get("X-Admin-Key")
    if key:
        return "key:" + hash_api_key(key)[:24]
    return "ip:" + get_remote_address(request)


# Jeden limiter współdzielony przez wszystkie routery.
# headers_enabled=True → w odpowiedzi pojawiają się nagłówki X-RateLimit-*,
# o ile endpoint przyjmuje parametr `response: Response` (patrz routery).
limiter = Limiter(key_func=rate_limit_key, headers_enabled=True)

# Domyślny limit dla endpointów (można nadpisać per trasa).
LIMIT_STRING = f"{settings.RATE_LIMIT_PER_MIN}/minute"
