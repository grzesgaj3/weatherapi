from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.errors import register_exception_handlers
from tests.helpers import ADMIN_HEADERS


async def test_body_too_large_returns_413(client, station):
    uid, api_key = station
    big = "x" * (70 * 1024)
    resp = await client.post(
        "/api/v1/measurements",
        json={"value": 1.0, "recorded_at": big},
        headers={"X-API-Key": api_key},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


async def test_rate_limit_headers_present(client, station):
    resp = await client.get("/api/v1/stations", headers=ADMIN_HEADERS)
    assert resp.status_code == 200
    # slowapi z headers_enabled dodaje nagłówki limitu na dekorowanych trasach.
    assert any(h.lower().startswith("x-ratelimit") for h in resp.headers)


def test_rate_limit_returns_429_envelope():
    """Przekroczenie limitu zwraca 429 w naszym envelope błędów."""
    limiter = Limiter(key_func=get_remote_address, headers_enabled=True)
    app = FastAPI()
    app.state.limiter = limiter
    register_exception_handlers(app)

    @app.get("/limited")
    @limiter.limit("2/minute")
    def limited(request: Request, response: Response):
        return {"ok": True}

    test_client = TestClient(app)
    assert test_client.get("/limited").status_code == 200
    assert test_client.get("/limited").status_code == 200
    resp = test_client.get("/limited")
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"
