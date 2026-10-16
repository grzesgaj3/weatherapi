from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi import status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_station
from app.api.pagination import decode_cursor, page_from_rows
from app.api.ratelimit import LIMIT_STRING, limiter
from app.database import get_db, utcnow
from app.models.measurement import Measurement
from app.models.station import Station
from app.schemas.common import Page
from app.schemas.measurement import MeasurementCreate, MeasurementRead

router = APIRouter(tags=["measurements"], prefix="/measurements")


@router.post(
    "",
    response_model=MeasurementRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Push pojedynczego pomiaru deszczomierza",
)
@limiter.limit(LIMIT_STRING)
async def create_measurement(
    request: Request,
    response: Response,
    payload: MeasurementCreate,
    station: Station = Depends(require_station),
    db: AsyncSession = Depends(get_db),
) -> MeasurementRead:
    """Przyjmuje pojedynczy pomiar opadu (mm).

    `received_at` ustawia serwer w momencie przyjęcia żądania.
    `recorded_at` to opcjonalny czas zakodowany w odebranej ramce radiowej
    (normalizowany do UTC).
    """
    measurement = Measurement(
        station_id=station.id,
        value=payload.value,
        received_at=utcnow(),
        recorded_at=payload.recorded_at,
    )
    db.add(measurement)
    await db.commit()
    await db.refresh(measurement)
    return MeasurementRead.model_validate(measurement)


@router.get(
    "",
    response_model=Page[MeasurementRead],
    summary="Lista pomiarów stacji (tylko dla uwierzytelnionej stacji)",
)
@limiter.limit(LIMIT_STRING)
async def list_measurements(
    request: Request,
    response: Response,
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = None,
    station: Station = Depends(require_station),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Measurement).where(Measurement.station_id == station.id)

    cur = decode_cursor(cursor) if cursor else {}
    last_id = cur.get("id")
    if last_id is not None:
        query = query.where(Measurement.id < int(last_id))

    query = query.order_by(Measurement.id.desc()).limit(limit + 1)
    rows = list((await db.execute(query)).scalars().all())
    page = page_from_rows(rows, limit, lambda m: {"id": m.id})
    page["data"] = [MeasurementRead.model_validate(m) for m in page["data"]]
    return page
