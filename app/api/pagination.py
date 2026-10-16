"""Pomocniki paginacji kursorowej (wg api-design: data / next_cursor / has_more)."""

import base64
import json
from collections.abc import Sequence
from typing import Any


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def page_from_rows(rows: Sequence[Any], limit: int, cursor_builder) -> dict[str, Any]:
    """Buduje envelope strony z listy pobranej jako `limit + 1` elementów.

    `cursor_builder(item)` zwraca dict z payloadem kursora dla ostatniego elementu.
    """
    has_more = len(rows) > limit
    items = list(rows[:limit])
    next_cursor = encode_cursor(cursor_builder(items[-1])) if has_more and items else None
    return {"data": items, "next_cursor": next_cursor, "has_more": has_more}
