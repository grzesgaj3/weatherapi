"""Narzędzia administracyjne (Typer)."""

import asyncio

import typer
from sqlalchemy import select

from app.database import AsyncSessionLocal, Base, async_engine
from app.models.station import Station
from app.services.security import generate_api_key, hash_api_key

cli = typer.Typer(help="Narzędzia administracyjne API pogodowego.", no_args_is_help=True)


def _run(coro):
    return asyncio.run(coro)


@cli.command("init-db")
def init_db() -> None:
    """Tworzy tabele na podstawie modeli (dev/quickstart)."""

    async def _init():
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    _run(_init())
    typer.echo("Tabele utworzone.")


@cli.command("add-station")
def add_station(
    uid: str = typer.Option(..., "--uid", help="Unikalny identyfikator, np. STACJA-001"),
    name: str = typer.Option(..., "--name", help="Nazwa przyjazna"),
    location: str = typer.Option(None, "--location", help="Opis lokalizacji"),
) -> None:
    """Rejestruje stację i wypisuje wygenerowany klucz API (tylko raz)."""
    api_key = generate_api_key()

    async def _add():
        async with AsyncSessionLocal() as db:
            existing = (
                await db.execute(select(Station).where(Station.station_uid == uid))
            ).scalar_one_or_none()
            if existing is not None:
                typer.secho(f"Stacja {uid} już istnieje.", fg=typer.colors.RED)
                raise typer.Exit(code=1)
            db.add(
                Station(
                    station_uid=uid,
                    name=name,
                    location=location,
                    api_key_hash=hash_api_key(api_key),
                )
            )
            await db.commit()

    _run(_add())
    typer.echo(f"Stacja: {uid}")
    typer.secho(f"API key: {api_key}", fg=typer.colors.GREEN)
    typer.echo("Zachowaj klucz – nie będzie ponownie wyświetlony.")


@cli.command("list-stations")
def list_stations() -> None:
    """Wyświetla wszystkie stacje."""

    async def _list():
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(select(Station).order_by(Station.id))).scalars().all()
            for s in rows:
                status = "aktywna" if s.is_active else "nieaktywna"
                typer.echo(f"[{s.id}] {s.station_uid} – {s.name} ({status})")

    _run(_list())


if __name__ == "__main__":
    cli()
