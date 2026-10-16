from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "tensor-forge", "time": datetime.now(timezone.utc).isoformat()}


@router.get("/", tags=["root"])
def root() -> dict[str, Any]:
    return {"service": "tensor-forge", "docs": "/docs", "health": "/health"}