"""SQLite persistence for forged manifests and audit log.

Sync SQLAlchemy 2.0 style engines so FastAPI sync routes and httpx-based tests
share a single connection model. ``init_db`` selects the storage URL so tests
can use an in-memory database.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.pool import StaticPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Forge(Base):
    __tablename__ = "forges"

    id: Mapped[int] = mapped_column(primary_key=True)
    program_name: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="python")
    source_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    # original source is retained for detail/export (size bounded by caller)
    source: Mapped[str] = mapped_column(nullable=False)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)

    @hybrid_property
    def command_count(self) -> int:
        data = self.result or {}
        return len(data.get("commands", []))


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(64), nullable=False)
    detail: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)


_Engine = None
SessionLocal = None


def get_engine():
    global _Engine
    if _Engine is None:
        url = settings.database_url
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _Engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _Engine


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(url: Optional[str] = None) -> None:
    """Create tables. If ``url`` is an in-memory SQLite database, a StaticPool
    is used so all threads (FastAPI + test client) share the connection.
    Call this at app startup (see ``app/main.py`` lifespan) or in tests."""
    global _Engine, SessionLocal
    if url is None:
        url = settings.database_url
    if url == "sqlite:///:memory:":
        engine = create_engine(url, connect_args={"check_same_thread": False},
                               poolclass=StaticPool)
    else:
        connect_args: dict = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    _Engine = engine
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)