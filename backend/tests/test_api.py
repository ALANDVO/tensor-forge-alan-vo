"""HTTP boundary tests using starlette TestClient over httpx.

These exercise the real routing, validation, persistence and response
envelope — not mocked handlers.
"""
from __future__ import annotations

import pytest
from fastapi import status

from app.services.forge import ForgeEngine

HELLO_SRC = '''
def hello(name: str, excited: bool = False) -> str:
    """Say hello."""
    return "hi"
'''


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["service"] == "tensor-forge"


def test_forge_endpoint_returns_manifest(client):
    r = client.post("/api/forge", json={"source": HELLO_SRC, "program_name": "hiapp"})
    assert r.status_code == 200
    body = r.json()
    assert body["program_name"] == "hiapp"
    assert body["error"] is None
    cmds = body["commands"]
    assert len(cmds) == 1
    assert cmds[0]["name"] == "hello"
    assert cmds[0]["rendered"].startswith("hiapp hello")
    assert "<NAME>" in cmds[0]["rendered"]


def test_forge_renders_bool_flag(client):
    r = client.post("/api/forge", json={"source": HELLO_SRC, "program_name": "app"})
    assert r.status_code == 200
    args = r.json()["commands"][0]["arguments"]
    excited = next(a for a in args if a["name"] == "excited")
    assert excited["cli_type"] == "boolean"
    assert excited["default"] == "False"


def test_forge_invalid_payload_missing_program_name(client):
    r = client.post("/api/forge", json={"source": HELLO_SRC})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_forge_blank_source_rejected(client):
    r = client.post("/api/forge", json={"source": "   ", "program_name": "app"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_forge_syntax_error_returns_422(client):
    r = client.post("/api/forge", json={
        "source": "def broken(:\n", "program_name": "app"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "Syntax error" in r.json()["detail"]


def test_forge_unsupported_language_returns_422(client):
    r = client.post("/api/forge", json={
        "source": "print(1)", "program_name": "app", "language": "rust"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "unsupported language" in r.json()["detail"]


def test_save_forge_persists_and_returns_detail(client):
    r = client.post("/api/forges", json={"source": HELLO_SRC, "program_name": "savedapp"})
    assert r.status_code == 201
    body = r.json()
    assert body["id"] is not None
    assert body["source"] == HELLO_SRC
    assert len(body["result"]["commands"]) == 1
    assert body["result"]["commands"][0]["name"] == "hello"


def test_list_forges_returns_saved(client):
    client.post("/api/forges", json={"source": HELLO_SRC, "program_name": "app-one"})
    client.post("/api/forges", json={"source": HELLO_SRC, "program_name": "app-two"})
    r = client.get("/api/forges")
    assert r.status_code == 200
    bodies = r.json()
    assert len(bodies) >= 2
    names = {b["program_name"] for b in bodies}
    assert {"app-one", "app-two"} <= names


def test_get_forge_detail(client):
    created = client.post("/api/forges", json={"source": HELLO_SRC, "program_name": "detail"})
    fid = created.json()["id"]
    r = client.get(f"/api/forges/{fid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == fid
    assert body["source_sha"]
    assert body["result"]["program_name"] == "detail"


def test_get_forge_not_found(client):
    r = client.get("/api/forges/999999")
    assert r.status_code == 404


def test_save_forge_audit_recorded(client):
    client.post("/api/forges", json={"source": HELLO_SRC, "program_name": "auditme"})
    r = client.get("/api/audit")
    assert r.status_code == 200
    actions = {row["action"] for row in r.json()}
    assert "create" in actions


def test_save_forge_syntax_error_does_not_persist(client):
    r = client.post("/api/forges", json={
        "source": "def broken(:\n", "program_name": "bad"})
    assert r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    list_r = client.get("/api/forges")
    assert all(b["program_name"] != "bad" for b in list_r.json())


def test_forge_command_count_matches_engine(client):
    # cross-check the HTTP envelope against the domain engine directly
    source = "def a(x): pass\ndef b(y: int): pass\n"
    http_body = client.post("/api/forge", json={"source": source, "program_name": "c"})\
        .json()
    expected = ForgeEngine().forge(source, "c")
    assert len(http_body["commands"]) == len(expected.commands)