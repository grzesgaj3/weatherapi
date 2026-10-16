import uuid
from datetime import datetime, timedelta

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base, utcnow

# Statusy kończące cykl życia zlecenia.
TERMINAL_STATUSES = ("completed", "failed", "cancelled", "expired")


class Command(Base):
    """Zlecenie dla stacji, np. czyszczenie deszczomierza."""

    __tablename__ = "commands"

    uid: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    params: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: utcnow() + timedelta(minutes=settings.COMMAND_TTL_MINUTES),
    )

    station = relationship("Station", back_populates="commands")

    __table_args__ = (
        Index("ix_commands_station_status", "station_id", "status"),
    )

    # --- Pomocnicze przejścia stanów ---

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def mark_delivered(self) -> None:
        if self.status == "pending":
            self.status = "delivered"
            self.delivered_at = utcnow()

    def mark_in_progress(self) -> None:
        self.status = "in_progress"
        if self.started_at is None:
            self.started_at = utcnow()

    def mark_completed(self, result: dict | None = None) -> None:
        self.status = "completed"
        self.result = result
        self.completed_at = utcnow()

    def mark_failed(self, result: dict | None = None) -> None:
        self.status = "failed"
        self.result = result
        self.completed_at = utcnow()

    def cancel(self) -> bool:
        if self.status in ("pending", "delivered"):
            self.status = "cancelled"
            self.completed_at = utcnow()
            return True
        return False
