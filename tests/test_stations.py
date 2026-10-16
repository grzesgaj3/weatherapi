from tests.helpers import ADMIN_HEADERS


async def test_duplicate_station_returns_409(client, station):
    uid, _ = station
    resp = await client.post(
        "/api/v1/stations",
        json={"station_uid": uid, "name": "duplikat"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "station_exists"


async def test_list_stations(client, station):
    resp = await client.get("/api/v1/stations", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert "api_key" not in resp.json()[0]


async def test_update_station(client, station):
    uid, _ = station
    resp = await client.patch(
        f"/api/v1/stations/{uid}",
        json={"is_active": False, "location": "Kraków"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert resp.json()["location"] == "Kraków"


async def test_inactive_station_cannot_push(client, station):
    uid, api_key = station
    await client.patch(
        f"/api/v1/stations/{uid}",
        json={"is_active": False},
        headers=ADMIN_HEADERS,
    )
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 1.0},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 401


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
