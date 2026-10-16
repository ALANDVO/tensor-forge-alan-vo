"""Shared pytest fixtures for tensor-forge backend tests.

Uses an in-memory SQLite database so tests are isolated and leave no files.
The ``DATABASE_URL`` env is set before importing the app so settings pick up
in-memory storage; ``init_db`` re-binds a fresh engine per fixture.
"""
from __future__ import annotations

import os

# Must precede any app import so pydantic-settings reads in-memory storage.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient

from app.models import db as _db
from app.main import create_app


@pytest.fixture()
def app():
    _db.init_db("sqlite:///:memory:")
    application = create_app()
    yield application


@pytest.fixture()
def client(app):
    # Entering the context triggers lifespan startup (which re-inits the db).
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def fresh_db():
    _db.init_db("sqlite:///:memory:")
    yield _db