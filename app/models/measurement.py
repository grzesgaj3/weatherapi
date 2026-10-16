from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Measurement(Base):
    """Pomiar opadu z deszczomierza (mm)."""

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)  # opad w mm
    # czas odbioru na serwerze (UTC)
    received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )  # czas zakodowany w odebranej ramce radiowej (jeśli dostarczony)

    station = relationship("Station", back_populates="measurements")

    __table_args__ = (
        Index("ix_measurements_station_received", "station_id", "received_at"),
        Index("ix_measurements_received_at", "received_at"),
    )
