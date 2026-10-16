from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.middleware import BodySizeLimitMiddleware
from app.api.ratelimit import limiter
from app.api.v1 import health
from app.api.v1.router import api_router
from app.config import settings


def create_app() -> FastAPI:
    docs_enabled = settings.ENABLE_DOCS or settings.DEBUG

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    # Limiter współdzielony z routerami (dekoratory @limiter.limit).
    app.state.limiter = limiter

    register_exception_handlers(app)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.MAX_BODY_BYTES)

    app.include_router(health.router)  # GET /health (bez limitu – sonduje liveness)
    app.include_router(api_router)  # /api/v1/*
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
