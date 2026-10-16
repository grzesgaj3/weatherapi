from tests.helpers import ADMIN_HEADERS


async def test_create_and_complete_clean_command(client, station):
    uid, api_key = station
    device_headers = {"X-API-Key": api_key}

    # Admin wystawia zlecenie czyszczenia.
    resp = await client.post(
        f"/api/v1/stations/{uid}/commands",
        json={"type": "clean_rain_gauge", "params": {"cycles": 3}},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    command = resp.json()
    assert command["status"] == "pending"
    assert command["params"] == {"cycles": 3}
    assert command["created_at"].endswith("Z")
    command_uid = command["uid"]

    # Read-only podgląd nie zmienia stanu.
    resp = await client.get("/api/v1/commands", headers=device_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"][0]["status"] == "pending"

    # Stacja pobiera (claim) – zlecenie oznaczone jako delivered.
    resp = await client.post("/api/v1/commands/claim", headers=device_headers)
    assert resp.status_code == 200, resp.text
    claimed = resp.json()
    assert len(claimed) == 1
    assert claimed[0]["uid"] == command_uid
    assert claimed[0]["status"] == "delivered"

    # Stacja potwierdza rozpoczęcie.
    resp = await client.post(
        f"/api/v1/commands/{command_uid}/ack",
        json={"status": "in_progress"},
        headers=device_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    # Stacja raportuje zakończenie.
    resp = await client.post(
        f"/api/v1/commands/{command_uid}/ack",
        json={"status": "completed", "result": {"duration_ms": 1200}},
        headers=device_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["result"] == {"duration_ms": 1200}

    # Admin widzi stan końcowy.
    resp = await client.get(f"/api/v1/commands/{command_uid}", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_only_one_active_command_per_station(client, station):
    uid, api_key = station
    payload = {"type": "clean_rain_gauge"}
    first = await client.post(
        f"/api/v1/stations/{uid}/commands", json=payload, headers=ADMIN_HEADERS
    )
    assert first.status_code == 201
    second = await client.post(
        f"/api/v1/stations/{uid}/commands", json=payload, headers=ADMIN_HEADERS
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "active_command_exists"


async def test_cancel_pending_command(client, station):
    uid, api_key = station
    resp = await client.post(
        f"/api/v1/stations/{uid}/commands",
        json={"type": "clean_rain_gauge"},
        headers=ADMIN_HEADERS,
    )
    command_uid = resp.json()["uid"]

    resp = await client.delete(f"/api/v1/commands/{command_uid}", headers=ADMIN_HEADERS)
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/commands/{command_uid}", headers=ADMIN_HEADERS)
    assert resp.json()["status"] == "cancelled"


async def test_ack_closed_command_returns_409(client, station):
    uid, api_key = station
    device_headers = {"X-API-Key": api_key}
    resp = await client.post(
        f"/api/v1/stations/{uid}/commands",
        json={"type": "clean_rain_gauge"},
        headers=ADMIN_HEADERS,
    )
    command_uid = resp.json()["uid"]
    await client.post(
        f"/api/v1/commands/{command_uid}/ack",
        json={"status": "completed"},
        headers=device_headers,
    )
    resp = await client.post(
        f"/api/v1/commands/{command_uid}/ack",
        json={"status": "completed"},
        headers=device_headers,
    )
    assert resp.status_code == 409


async def test_admin_can_filter_by_status(client, station):
    uid, api_key = station
    resp = await client.post(
        f"/api/v1/stations/{uid}/commands",
        json={"type": "clean_rain_gauge"},
        headers=ADMIN_HEADERS,
    )
    command_uid = resp.json()["uid"]
    await client.delete(f"/api/v1/commands/{command_uid}", headers=ADMIN_HEADERS)

    resp = await client.get(
        f"/api/v1/stations/{uid}/commands",
        headers=ADMIN_HEADERS,
        params={"status": "cancelled"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"][0]["status"] == "cancelled"


async def test_device_cannot_access_admin_endpoints(client, station):
    uid, api_key = station
    resp = await client.post(
        f"/api/v1/stations/{uid}/commands",
        json={"type": "clean_rain_gauge"},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_admin_token"


async def test_unknown_command_returns_404(client, station):
    uid, api_key = station
    resp = await client.get("/api/v1/commands/nie-ma-takiego", headers=ADMIN_HEADERS)
    assert resp.status_code == 404
