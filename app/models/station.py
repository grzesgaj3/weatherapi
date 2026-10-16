from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class Station(Base):
    """Stacja z deszczomierzem."""

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    station_uid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Przechowujemy wyłącznie hash klucza API, nigdy wartość jawną.
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)

    measurements = relationship(
        "Measurement",
        back_populates="station",
        cascade="all, delete-orphan",
    )
    commands = relationship(
        "Command",
        back_populates="station",
        cascade="all, delete-orphan",
    )
