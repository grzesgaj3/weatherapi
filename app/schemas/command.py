from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.common import to_utc_iso

CommandType = Literal["clean_rain_gauge", "reset", "calibrate"]
AckStatus = Literal["in_progress", "completed", "failed"]


class CommandCreate(BaseModel):
    """Zlecenie wystawiane przez operatora (admin)."""

    model_config = ConfigDict(extra="forbid")

    type: CommandType = "clean_rain_gauge"
    params: dict | None = None


class CommandAck(BaseModel):
    """Kwitowanie zlecenia przez stację."""

    model_config = ConfigDict(extra="forbid")

    status: AckStatus
    result: dict | None = None


class CommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str
    station_id: int
    type: str
    status: str
    params: dict | None
    result: dict | None
    created_by: str | None
    created_at: datetime
    delivered_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    expires_at: datetime

    @field_serializer(
        "created_at",
        "delivered_at",
        "started_at",
        "completed_at",
        "expires_at",
    )
    def _serialize_utc(self, value: datetime | None) -> str | None:
        return to_utc_iso(value)
