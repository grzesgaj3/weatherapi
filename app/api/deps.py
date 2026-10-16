from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.station import Station
from app.schemas.common import error_response
from app.services.security import hash_api_key, verify_admin_token


async def require_station(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Station:
    """Uwierzytelnia stację po nagłówku X-API-Key. Zwraca obiekt Station."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("missing_api_key", "Brak nagłówka X-API-Key"),
        )

    key_hash = hash_api_key(x_api_key)
    result = await db.execute(
        select(Station).where(
            Station.api_key_hash == key_hash,
            Station.is_active.is_(True),
        )
    )
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("invalid_api_key", "Nieprawidłowy lub nieaktywny klucz API"),
        )
    return station


async def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    authorization: str | None = Header(default=None),
) -> str:
    """Uwierzytelnia operatora/admina. Zwraca identyfikator wywołującego."""
    token = x_admin_key
    if not token and authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer" and value:
            token = value.strip()

    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("invalid_admin_token", "Nieprawidłowy token administratora"),
        )
    return "admin"
