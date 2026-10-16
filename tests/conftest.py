import os

# Ustawiane przed importem app.config, aby Settings() przeszedł walidację
# i nie trafiał w rate limit w testach.
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token-0123456789abcdef")
os.environ.setdefault("RATE_LIMIT_PER_MIN", "100000")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def station(client):
    """Rejestruje stację i zwraca (station_uid, api_key)."""
    from tests.helpers import ADMIN_HEADERS

    payload = {"station_uid": "STACJA-001", "name": "Ogród", "location": "Warszawa"}
    resp = await client.post("/api/v1/stations", json=payload, headers=ADMIN_HEADERS)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["station_uid"], body["api_key"]
