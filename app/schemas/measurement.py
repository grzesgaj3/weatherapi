from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.common import normalize_to_naive_utc, to_utc_iso


class MeasurementCreate(BaseModel):
    """Pojedynczy pomiar opadu z deszczomierza."""

    model_config = ConfigDict(extra="forbid")

    value: float = Field(ge=0, le=99999.99, description="Opad w mm")
    recorded_at: datetime | None = Field(
        default=None,
        description="Czas zakodowany odebrany ze stacji radiowej (opcjonalny).",
    )

    @field_validator("recorded_at")
    @classmethod
    def _to_utc(cls, value: datetime | None) -> datetime | None:
        # Ujednolicamy do naive UTC niezależnie od offsetu wejściowego.
        return normalize_to_naive_utc(value)


class MeasurementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    value: float
    received_at: datetime
    recorded_at: datetime | None

    @field_serializer("received_at", "recorded_at")
    def _serialize_utc(self, value: datetime | None) -> str | None:
        return to_utc_iso(value)
