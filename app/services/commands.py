"""Logika cyklu życia zleceń (commands)."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import utcnow
from app.models.command import Command
from app.models.station import Station

# Aktywne = jeszcze nierozliczone zlecenia.
ACTIVE_STATUSES = ("pending", "delivered", "in_progress")


class ActiveCommandExists(Exception):
    """Istnieje już aktywne zlecenie danego typu dla tej stacji."""


async def _expire_stale(db: AsyncSession, station_id: int) -> None:
    """Oznacza przeterminowane zlecenia stacji jako `expired`.

    Nie commituje – ma działać w tej samej transakcji co operacja, która
    ją wywołała (m.in. po to, by nie zwalniać blokady wiersza stacji).
    """
    now = utcnow()
    result = await db.execute(
        select(Command).where(
            Command.station_id == station_id,
            Command.status.in_(("pending", "delivered")),
            Command.expires_at < now,
        )
    )
    for cmd in result.scalars().all():
        cmd.status = "expired"
        cmd.completed_at = now
    # autoflush=False → wymuszamy UPDATE, aby kolejne SELECT-y widziały zmianę
    # (w tej samej transakcji, bez jej zamykania).
    await db.flush()


async def count_active_commands(db: AsyncSession, station_id: int, cmd_type: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Command)
        .where(
            Command.station_id == station_id,
            Command.type == cmd_type,
            Command.status.in_(ACTIVE_STATUSES),
        )
    )
    return int(result.scalar_one())


async def create_command(
    db: AsyncSession,
    station: Station,
    cmd_type: str,
    params: dict | None,
    created_by: str | None,
) -> Command:
    # Blokada wiersza stacji serializuje równoległe tworzenie zleceń
    # (check-then-insert), a wygaśnięcie i INSERT są w tej samej transakcji.
    await db.execute(
        select(Station.id).where(Station.id == station.id).with_for_update()
    )
    await _expire_stale(db, station.id)

    active = await count_active_commands(db, station.id, cmd_type)
    if active >= settings.MAX_ACTIVE_COMMANDS_PER_STATION:
        await db.rollback()  # zwalnia blokadę
        raise ActiveCommandExists(cmd_type)

    command = Command(
        station_id=station.id,
        type=cmd_type,
        status="pending",
        params=params,
        created_by=created_by,
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)
    return command


async def claim_commands(db: AsyncSession, station: Station) -> list[Command]:
    """Pobranie (claim) aktywnych zleceń przez stację.

    Wygasza przeterminowane i oznacza pobrane `pending` jako `delivered`.
    Operacja zapisu – udostępniana przez POST, nie GET.
    """
    await _expire_stale(db, station.id)

    result = await db.execute(
        select(Command)
        .where(
            Command.station_id == station.id,
            Command.status.in_(ACTIVE_STATUSES),
        )
        .order_by(Command.created_at.asc())
    )
    rows = list(result.scalars().all())

    for cmd in rows:
        if cmd.status == "pending":
            cmd.mark_delivered()

    await db.commit()
    return rows
