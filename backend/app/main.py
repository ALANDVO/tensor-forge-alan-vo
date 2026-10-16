"""tensor-forge application factory.

Usage:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
or via Docker: CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.forge import router as forge_router
from app.api.health import router as health_router
from app.core.config import settings
from app.models import db  # noqa: F401  (ensures tables/init on import)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure schema exists for the configured (or test-overridden) database
    db.init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="tensor-forge",
        description="Forge agent-native CLI command manifests from source code.",
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.include_router(health_router)
    app.include_router(forge_router, prefix="/api")

    @app.exception_handler(Exception)
    async def _unhandled(request, exc):  # pragma: no cover - defensive
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=500, content={"detail": "internal server error"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)