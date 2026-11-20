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

    # OIDC Keycloak authentication routes
    KEYCLOAK_URL = "https://auth.example.com/realms/tensor-forge"
    KEYCLOAK_CLIENT_ID = "tensor-forge-client"
    KEYCLOAK_REDIRECT_URI = "http://127.0.0.1:8000/api/oidc/callback"

    # In-memory auth state (per-process; production would use Redis)
    _STORE: dict[str, dict[str, Any]] = {}

    def _generate_pkce():
        verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(verifier.encode("utf-8")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return {"verifier": verifier, "challenge": challenge}

    def _state_param():
        state = secrets.token_urlsafe(16)
        _STORE[state] = {"verifier": _generate_pkce()["verifier"], "nonce": secrets.token_urlsafe(16)}
        return state

    @app.get("/api/oidc/authorize")
    async def oidc_authorize():
        """Initiate Keycloak authorization code flow with PKCE."""
        state = _state_param()
        params = {
            "response_type": "code",
            "client_id": KEYCLOAK_CLIENT_ID,
            "redirect_uri": KEYCLOAK_REDIRECT_URI,
            "scope": "openid profile email",
            "state": state,
            "code_challenge": _generate_pkce()["challenge"],
            "code_challenge_method": "S256",
            "prompt": "login",
        }
        url = f"{KEYCLOAK_URL}/protocol/openid/authorize?{urllib.parse.urlencode(params)}"
        return Response(status_code=302, headers={"Location": url})

    @app.get("/api/oidc/callback")
    async def oidc_callback(request: Request):
        """Handle Keycloak callback with authorization code."""
        error = request.query_params.get("error")
        if error:
            return Response(content=f"Authentication failed: {error}", status_code=400)
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        if not code or not state:
            return Response(content="Missing code or state parameter", status_code=400)
        stored = _STORE.get(state)
        if stored is None:
            return Response(content="Invalid or expired state", status_code=400)
        _STORE.pop(state, None)
        session_token = base64.urlsafe_b64encode(
            f"oidc:nonce={stored['nonce']}:state={state}".encode()
        ).decode().rstrip("=")
        return Response(
            status_code=302,
            headers={"Location": "http://127.0.0.1:5173?token=" + session_token},
        )

    @app.get("/api/oidc/userinfo")
    async def oidc_userinfo(token: str = ...):
        """Minimal userinfo endpoint - validates session token format."""
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = {}
            for seg in decoded.split(":"):
                if "=" in seg:
                    k, v = seg.split("=", 1)
                    parts[k] = v
            return {
                "sub": parts.get("state", "unknown"),
                "nonce": parts.get("nonce", "unknown"),
                "expires": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=400, content={"detail": "invalid token"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
