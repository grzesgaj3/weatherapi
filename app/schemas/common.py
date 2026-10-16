"""Wspólne modele i pomocniki odpowiedzi API."""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar, overload

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Ujednolicony envelope błędów: {"error": {...}}."""

    error: ErrorBody


class Page(BaseModel, Generic[T]):
    """Envelope list z paginacją kursorową (wg api-design)."""

    data: list[T]
    next_cursor: str | None = None
    has_more: bool = False


def error_response(
    code: str, message: str, details: list[dict[str, Any]] | None = None
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        }
    }


@overload
def to_utc_iso(value: None) -> None: ...


@overload
def to_utc_iso(value: datetime) -> str: ...


def to_utc_iso(value: datetime | None) -> str | None:
    """Serializacja naive-UTC (z bazy) do ISO 8601 z sufiksem 'Z'."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def normalize_to_naive_utc(value: datetime | None) -> datetime | None:
    """Konwersja dowolnej daty (aware/naive) do naive UTC (MySQL DATETIME)."""
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value
