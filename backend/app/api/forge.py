from __future__ import annotations

import hashlib
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import AuditLog, Forge, get_session
from app.models.schema import (
    ForgeDetailSchema,
    ForgeRequest,
    ForgeResponse,
    SavedForgeSchema,
)
from app.services.audit import audit
from app.services.forge import ForgeEngine

router = APIRouter(tags=["forge"])


def _run_engine(payload: ForgeRequest) -> tuple[ForgeEngine, Any]:
    engine = ForgeEngine()
    result = engine.forge(payload.source, payload.program_name, payload.language)
    return engine, result


@router.post("/forge", response_model=ForgeResponse, status_code=200)
def forge(payload: Annotated[ForgeRequest, Body()]) -> ForgeResponse:
    """Analyze source and return a forged CLI manifest (stateless compute)."""
    _engine, result = _run_engine(payload)
    if result.error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=result.error)
    return _to_response(result)


@router.post("/forges", response_model=ForgeDetailSchema, status_code=201)
def save_forge(
    payload: Annotated[ForgeRequest, Body()],
    session: Annotated[Session, Depends(get_session)],
) -> ForgeDetailSchema:
    """Forge from source and persist the manifest."""
    _engine, result = _run_engine(payload)
    if result.error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=result.error)

    source_sha = hashlib.sha256(payload.source.encode("utf-8")).hexdigest()
    db_forge = Forge(
        program_name=payload.program_name,
        language=payload.language,
        source_sha=source_sha,
        source=payload.source,
        result=result.to_dict(),
    )
    session.add(db_forge)
    session.add(audit(session, "create", "forge", f"program={payload.program_name}"))
    session.commit()
    session.refresh(db_forge)
    return db_forge


@router.get("/forges", response_model=list[SavedForgeSchema])
def list_forges(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[SavedForgeSchema]:
    return (session.execute(select(Forge).order_by(Forge.id.desc()).limit(limit).offset(offset))
            .scalars().all())


@router.get("/forges/{forge_id}", response_model=ForgeDetailSchema)
def get_forge(
    session: Annotated[Session, Depends(get_session)],
    forge_id: int,
) -> ForgeDetailSchema:
    db_forge = session.get(Forge, forge_id)
    if not db_forge:
        raise HTTPException(status_code=404, detail="forge not found")
    session.add(audit(session, "read", "forge", f"id={forge_id}"))
    session.commit()
    return db_forge


@router.get("/audit", response_model=list[dict[str, Any]])
def audit_log(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    rows = session.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)).scalars().all()
    return [{"action": r.action, "resource": r.resource, "detail": r.detail,
             "created_at": r.created_at.isoformat()} for r in rows]


def _to_response(result) -> ForgeResponse:
    return ForgeResponse(
        program_name=result.program_name,
        language=result.language,
        commands=[_cmd_schema(c) for c in result.commands],
        error=result.error,
    )


def _cmd_schema(c):
    return {
        "name": c.name, "kind": c.kind, "docstring": c.docstring,
        "location": c.location, "rendered": c.rendered,
        "arguments": [_arg_schema(a) for a in c.arguments],
    }


def _arg_schema(a):
    return {
        "name": a.name, "py_type": a.py_type, "cli_type": a.cli_type,
        "required": a.required, "default": a.default, "help": a.help,
    }


__all__ = ["router"]