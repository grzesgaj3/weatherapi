from fastapi import APIRouter

from app.api.v1 import commands, measurements, stations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(measurements.router)
api_router.include_router(commands.router)
api_router.include_router(stations.router)
