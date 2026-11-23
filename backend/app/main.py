"""tensor-forge application factory.

Usage:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
or via Docker: CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timezone

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status

from app.api.forge import router as forge_router
from app.api.health import router as health_router
from app.core.config import settings
from app.models import db  # noqa: F401  (ensures tables/init on import)
from app.api.oidc import router as oidc_router


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

    # Include existing routers
    app.include_router(health_router)
    app.include_router(forge_router, prefix="/api")
    app.include_router(oidc_router, prefix="/api/oidc")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
