import secrets
import click
from app import create_app
from models import db, Station

app = create_app()


@click.group()
def cli():
    """Narzędzia administracyjne API pogodowego."""


@cli.command("init-db")
def init_db():
    """Tworzy tabele w bazie (na podstawie modeli)."""
    with app.app_context():
        db.create_all()
        click.echo("Tabele utworzone.")


@cli.command("add-station")
@click.option("--uid", required=True, help="Unikalny identyfikator stacji, np. STACJA-001")
@click.option("--name", required=True, help="Nazwa przyjazna")
@click.option("--location", default=None, help="Opis lokalizacji")
def add_station(uid, name, location):
    """Rejestruje nową stację i wypisuje wygenerowany API key."""
    with app.app_context():
        if Station.query.filter_by(station_uid=uid).first():
            raise click.ClickException(f"Stacja {uid} już istnieje.")

        api_key = secrets.token_hex(32)
        st = Station(station_uid=uid, name=name, location=location, api_key=api_key)
        db.session.add(st)
        db.session.commit()

        click.echo(f"Stacja: {uid}")
        click.echo(f"API key: {api_key}")
        click.echo("Zachowaj klucz – nie będzie ponownie wyświetlony.")


@cli.command("list-stations")
def list_stations():
    """Wyświetla wszystkie stacje."""
    with app.app_context():
        for s in Station.query.order_by(Station.id).all():
            status = "aktywna" if s.is_active else "nieaktywna"
            click.echo(f"[{s.id}] {s.station_uid} – {s.name} ({status})")


if __name__ == "__main__":
    cli()