from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi import status as http_status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_station
from app.api.pagination import decode_cursor, page_from_rows
from app.api.ratelimit import LIMIT_STRING, limiter
from app.database import get_db
from app.models.command import Command
from app.models.station import Station
from app.schemas.command import CommandAck, CommandRead
from app.schemas.common import Page, error_response
from app.services.commands import ACTIVE_STATUSES, claim_commands

router = APIRouter(tags=["commands"], prefix="/commands")


# ---------------------------------------------------------------------------
# Endpointy urządzenia (auth: X-API-Key stacji)
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=Page[CommandRead],
    summary="Podgląd zleceń zalogowanej stacji (bez zmiany stanu)",
)
@limiter.limit(LIMIT_STRING)
async def list_my_commands(
    request: Request,
    response: Response,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    station: Station = Depends(require_station),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Odczyt zleceń stacji. Domyślnie zwraca aktywne (`pending`/`delivered`/`in_progress`).

    To operacja tylko do odczytu – pobranie (i oznaczenie jako `delivered`)
    realizuje `POST /commands/claim`.
    """
    query = select(Command).where(Command.station_id == station.id)
    if status:
        query = query.where(Command.status == status)
    else:
        query = query.where(Command.status.in_(ACTIVE_STATUSES))

    cur = decode_cursor(cursor) if cursor else {}
    created_at, uid = cur.get("created_at"), cur.get("uid")
    if created_at and uid:
        dt = datetime.fromisoformat(created_at)
        query = query.where(
            or_(
                Command.created_at < dt,
                and_(Command.created_at == dt, Command.uid < uid),
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


@router.post(
    "/claim",
    response_model=list[CommandRead],
    summary="Pobranie (claim) zleceń przez stację",
)
@limiter.limit(LIMIT_STRING)
async def claim_my_commands(
    request: Request,
    response: Response,
    station: Station = Depends(require_station),
    db: AsyncSession = Depends(get_db),
) -> list[CommandRead]:
    """Stacja pobiera aktywne zlecenia. Wygasza przeterminowane i oznacza
    pobrane `pending` jako `delivered`."""
    rows = await claim_commands(db, station)
    return [CommandRead.model_validate(c) for c in rows]


@router.post(
    "/{uid}/ack",
    response_model=CommandRead,
    summary="Kwitowanie zlecenia przez stację",
)
@limiter.limit(LIMIT_STRING)
async def ack_command(
    request: Request,
    response: Response,
    uid: str,
    payload: CommandAck,
    station: Station = Depends(require_station),
    db: AsyncSession = Depends(get_db),
) -> CommandRead:
    result = await db.execute(
        select(Command).where(Command.uid == uid, Command.station_id == station.id)
    )
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=error_response("command_not_found", "Nie znaleziono zlecenia"),
        )
    if command.is_terminal:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=error_response(
                "command_closed", f"Zlecenie jest już zamknięte ({command.status})"
            ),
        )

    if payload.status == "in_progress":
        command.mark_in_progress()
    elif payload.status == "completed":
        command.mark_completed(payload.result)
    elif payload.status == "failed":
        command.mark_failed(payload.result)

    await db.commit()
    await db.refresh(command)
    return CommandRead.model_validate(command)


# ---------------------------------------------------------------------------
# Endpointy administratora (auth: X-Admin-Key / Bearer)
# ---------------------------------------------------------------------------
@router.get(
    "/{uid}",
    response_model=CommandRead,
    summary="Szczegóły zlecenia (admin)",
)
@limiter.limit(LIMIT_STRING)
async def get_command(
    request: Request,
    response: Response,
    uid: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> CommandRead:
    result = await db.execute(select(Command).where(Command.uid == uid))
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=error_response("command_not_found", "Nie znaleziono zlecenia"),
        )
    return CommandRead.model_validate(command)


@router.delete(
    "/{uid}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Anulowanie zlecenia (admin)",
)
@limiter.limit(LIMIT_STRING)
async def cancel_command(
    request: Request,
    response: Response,
    uid: str,
    _: str = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Command).where(Command.uid == uid))
    command = result.scalar_one_or_none()
    if command is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=error_response("command_not_found", "Nie znaleziono zlecenia"),
        )
    if not command.cancel():
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=error_response(
                "command_not_cancellable",
                f"Nie można anulować zlecenia w stanie {command.status}",
            ),
        )
    await db.commit()
