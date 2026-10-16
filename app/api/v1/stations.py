from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi import status as http_status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.api.pagination import decode_cursor, page_from_rows
from app.api.ratelimit import LIMIT_STRING, limiter
from app.database import get_db
from app.models.command import Command
from app.models.measurement import Measurement
from app.models.station import Station
from app.schemas.command import CommandCreate, CommandRead
from app.schemas.common import Page, error_response
from app.schemas.measurement import MeasurementRead
from app.schemas.station import (
    StationCreate,
    StationCreated,
    StationRead,
    StationUpdate,
)
from app.services.commands import ActiveCommandExists, create_command
from app.services.security import generate_api_key, hash_api_key

router = APIRouter(tags=["stations"], prefix="/stations")


async def _get_station_or_404(db: AsyncSession, uid: str) -> Station:
    result = await db.execute(select(Station).where(Station.station_uid == uid))
    station = result.scalar_one_or_none()
    if station is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=error_response("station_not_found", "Nie znaleziono stacji"),
        )
    return station


@router.post(
    "",
    response_model=StationCreated,
    status_code=http_status.HTTP_201_CREATED,
    summary="Rejestracja stacji (admin) – zwraca klucz API tylko raz",
)
@limiter.limit(LIMIT_STRING)
async def create_station(
    request: Request,
    response: Response,
    payload: StationCreate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StationCreated:
    api_key = generate_api_key()
    station = Station(
        station_uid=payload.station_uid,
        name=payload.name,
        location=payload.location,
        api_key_hash=hash_api_key(api_key),
    )
    db.add(station)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=error_response(
                "station_exists", f"Stacja {payload.station_uid} już istnieje"
            ),
        ) from exc
    await db.refresh(station)
    data = StationRead.model_validate(station).model_dump()
    return StationCreated(**data, api_key=api_key)


@router.get("", response_model=list[StationRead], summary="Lista stacji (admin)")
@limiter.limit(LIMIT_STRING)
async def list_stations(
    request: Request,
    response: Response,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[StationRead]:
    rows = (await db.execute(select(Station).order_by(Station.id))).scalars().all()
    return [StationRead.model_validate(s) for s in rows]


@router.get("/{uid}", response_model=StationRead, summary="Szczegóły stacji (admin)")
@limiter.limit(LIMIT_STRING)
async def get_station(
    request: Request,
    response: Response,
    uid: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StationRead:
    station = await _get_station_or_404(db, uid)
    return StationRead.model_validate(station)


@router.patch("/{uid}", response_model=StationRead, summary="Aktualizacja stacji (admin)")
@limiter.limit(LIMIT_STRING)
async def update_station(
    request: Request,
    response: Response,
    uid: str,
    payload: StationUpdate,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> StationRead:
    station = await _get_station_or_404(db, uid)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(station, field, value)
    await db.commit()
    await db.refresh(station)
    return StationRead.model_validate(station)


@router.post(
    "/{uid}/commands",
    response_model=CommandRead,
    status_code=http_status.HTTP_201_CREATED,
    summary="Wystawienie zlecenia dla stacji (admin), np. czyszczenie deszczomierza",
)
@limiter.limit(LIMIT_STRING)
async def create_station_command(
    request: Request,
    response: Response,
    uid: str,
    payload: CommandCreate,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CommandRead:
    station = await _get_station_or_404(db, uid)
    try:
        command = await create_command(
            db, station, payload.type, payload.params, created_by=admin
        )
    except ActiveCommandExists as exc:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=error_response(
                "active_command_exists",
                f"Stacja {uid} ma już aktywne zlecenie typu {payload.type}",
            ),
        ) from exc
    return CommandRead.model_validate(command)


@router.get(
    "/{uid}/commands",
    response_model=Page[CommandRead],
    summary="Kolejka zleceń stacji (admin)",
)
@limiter.limit(LIMIT_STRING)
async def list_station_commands(
    request: Request,
    response: Response,
    uid: str,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = None,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    station = await _get_station_or_404(db, uid)
    query = select(Command).where(Command.station_id == station.id)
    if status:
        query = query.where(Command.status == status)

    cur = decode_cursor(cursor) if cursor else {}
    created_at, cmd_uid = cur.get("created_at"), cur.get("uid")
    if created_at and cmd_uid:
        dt = datetime.fromisoformat(created_at)
        query = query.where(
            or_(
                Command.created_at < dt,
                and_(Command.created_at == dt, Command.uid < cmd_uid),
            )
        )

    query = (
        query.order_by(Command.created_at.desc(), Command.uid.desc()).limit(limit + 1)
    )
    rows = list((await db.execute(query)).scalars().all())
    page = page_from_rows(
        rows,
        limit,
        lambda c: {"created_at": c.created_at.isoformat(), "uid": c.uid},
    )
    page["data"] = [CommandRead.model_validate(c) for c in page["data"]]
    return page


@router.get(
    "/{uid}/measurements",
    response_model=Page[MeasurementRead],
    summary="Pomiary stacji (admin)",
)
@limiter.limit(LIMIT_STRING)
async def list_station_measurements(
    request: Request,
    response: Response,
    uid: str,
    limit: int = Query(default=100, ge=1, le=1000),
    cursor: str | None = None,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    station = await _get_station_or_404(db, uid)
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
