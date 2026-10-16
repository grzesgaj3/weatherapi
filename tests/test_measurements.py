from tests.helpers import ADMIN_HEADERS  # noqa: F401  (używane przez inne testy)


async def test_push_measurement_ok(client, station):
    uid, api_key = station
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 12.5},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert float(body["value"]) == 12.5
    assert body["received_at"].endswith("Z")
    assert body["recorded_at"] is None


async def test_push_measurement_converts_offset_to_utc(client, station):
    """recorded_at z offsetem musi trafić do bazy jako UTC."""
    uid, api_key = station
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 3.0, "recorded_at": "2026-10-12T08:45:00+02:00"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["recorded_at"] == "2026-10-12T06:45:00Z"


async def test_push_without_key_returns_401(client):
    resp = await client.post("/api/v1/measurements", json={"value": 1.0})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "missing_api_key"


async def test_push_with_invalid_key_returns_401(client):
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 1.0},
        headers={"X-API-Key": "nie-ma-takiego"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"


async def test_push_negative_value_returns_422(client, station):
    uid, api_key = station
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": -1.0},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


async def test_push_unknown_field_returns_422(client, station):
    uid, api_key = station
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 1.0, "temperature": 20},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 422


async def test_list_measurements_paginated(client, station):
    uid, api_key = station
    for v in (1.0, 2.0, 3.0):
        await client.post(
            "/api/v1/measurements",
            json={"value": v},
            headers={"X-API-Key": api_key},
        )
    resp = await client.get(
        "/api/v1/measurements", headers={"X-API-Key": api_key}, params={"limit": 2}
    )
    assert resp.status_code == 200
    page = resp.json()
    assert len(page["data"]) == 2
    assert page["has_more"] is True
    assert page["next_cursor"]

    # Następna strona przez kursor.
    resp2 = await client.get(
        "/api/v1/measurements",
        headers={"X-API-Key": api_key},
        params={"limit": 2, "cursor": page["next_cursor"]},
    )
    page2 = resp2.json()
    assert len(page2["data"]) == 1
    assert page2["has_more"] is False
    assert page2["next_cursor"] is None
