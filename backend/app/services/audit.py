"""Lightweight audit log writer."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.db import AuditLog


def audit(session: Session, action: str, resource: str,
          detail: Optional[str] = None) -> AuditLog:
    entry = AuditLog(action=action, resource=resource, detail=detail)
    session.add(entry)
    return entry


def recent_actions(session: Session, limit: int = 50) -> list[AuditLog]:
    return (session.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .limit(limit)
            .all())