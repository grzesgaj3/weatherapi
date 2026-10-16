from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.common import to_utc_iso


class StationCreate(BaseModel):
    station_uid: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)


class StationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class StationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_uid: str
    name: str
    location: str | None
    is_active: bool
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_utc(self, value: datetime) -> str:
        return to_utc_iso(value)


class StationCreated(StationRead):
    """Zwracane tylko raz – zawiera jawny klucz API."""

    api_key: str
