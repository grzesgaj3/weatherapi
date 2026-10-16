from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.database import utcnow
from app.models.command import Command
from app.models.station import Station
from app.services.commands import (
    claim_commands,
    count_active_commands,
    create_command,
)
from app.services.security import hash_api_key


async def _make_station(session) -> Station:
    station = Station(
        station_uid="STACJA-TTL",
        name="TTL",
        api_key_hash=hash_api_key("klucz-testowy"),
    )
    session.add(station)
    await session.commit()
    await session.refresh(station)
    return station


async def test_claim_expires_stale_command(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        station = await _make_station(session)
        stale = Command(
            station_id=station.id,
            type="clean_rain_gauge",
            status="pending",
            expires_at=utcnow() - timedelta(minutes=1),
        )
        session.add(stale)
        await session.commit()

        rows = await claim_commands(session, station)

        assert rows == []
        assert stale.status == "expired"


async def test_expired_command_frees_active_slot(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        station = await _make_station(session)
        old = Command(
            station_id=station.id,
            type="clean_rain_gauge",
            status="pending",
            expires_at=utcnow() - timedelta(minutes=1),
        )
        session.add(old)
        await session.commit()

        assert await count_active_commands(session, station.id, "clean_rain_gauge") == 1

        # Wygasłe zlecenie nie blokuje nowego – create_command najpierw je wygasa.
        new = await create_command(
            session, station, "clean_rain_gauge", None, created_by="admin"
        )
        assert new.status == "pending"
        assert old.status == "expired"
