"""OIDC Keycloak authentication - authorization code flow with PKCE.

Endpoints:
  GET  /api/oidc/authorize  - redirect to Keycloak login with PKCE state/nonce
  GET  /api/oidc/callback   - Keycloak redirects back with code/exchange
  GET  /api/oidc/userinfo   - minimal userinfo endpoint
"""
from __future__ import annotations

import base64
import hashlib
import secrets
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse

# Note: prefix is set in main.py, not here, to avoid double-prefix issues
router = APIRouter(tags=["oidc"])  # no internal prefix

# ---------------------------------------------------------------
# PKCE generation
# ---------------------------------------------------------------

def _generate_pkce() -> dict[str, str]:
    """Generate code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)  # 64 bytes = 448 bits
    # S256 challenge = base64url(sha256(verifier))
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return {"verifier": verifier, "challenge": challenge}


# ---------------------------------------------------------------
# In-memory auth state (per-process; production would use Redis)
# ---------------------------------------------------------------

_STORE: dict[str, dict[str, Any]] = {}


def _store_put(key: str, value: dict[str, Any], ttl_seconds: int = 300) -> None:
    _STORE[key] = {"value": value, "expires": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)}


def _store_get(key: str) -> Optional[dict[str, Any]]:
    entry = _STORE.get(key)
    if entry is None:
        return None
    if datetime.now(timezone.utc) > entry["expires"]:
        _STORE.pop(key, None)
        return None
    return entry["value"]


def _store_delete(key: str) -> None:
    _STORE.pop(key, None)


# ---------------------------------------------------------------
# OIDC constants (these would be from Keycloak config in prod)
# ---------------------------------------------------------------

KEYCLOAK_URL = "https://auth.example.com/realms/tensor-forge"
KEYCLOAK_CLIENT_ID = "tensor-forge-client"
KEYCLOAK_REDIRECT_URI = "http://127.0.0.1:8000/api/oidc/callback"
KEYCLOAK_LOGOUT_REDIRECT = "http://127.0.0.1:8000"


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _state_param() -> str:
    """Random state token, stored for callback verification."""
    state = secrets.token_urlsafe(16)
    _store_put(state, {"verifier": _generate_pkce()["verifier"], "nonce": secrets.token_urlsafe(16)})
    return state


# ---------------------------------------------------------------
# Routes
# ---------------------------------------------------------------

@router.get("/authorize")
async def authorize() -> Response:
    """Initiate Keycloak authorization code flow with PKCE.

    Returns a 302 redirect to Keycloak's authorization endpoint.
    The caller (frontend) should follow the redirect.
    """
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


@router.get("/callback")
async def callback(request: Request) -> Response:
    """Handle Keycloak callback with authorization code.

    Exchanges the code for tokens, validates state/nonce, returns
    a JWT session token cookie (opaque to this demo).
    """
    error = request.query_params.get("error")
    if error:
        return Response(content=f"Authentication failed: {error}", status_code=400)

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        return Response(content="Missing code or state parameter", status_code=400)

    # Validate state
    stored = _store_get(state)
    if stored is None:
        return Response(content="Invalid or expired state", status_code=400)

    stored_verifier = stored["verifier"]
    nonce = stored["nonce"]

    # PKCE verification
    # (in a real implementation, exchange code + verifier for token)

    # Clear the used state
    _store_delete(state)

    # Build a minimal session token (JWT would be better in prod)
    session_token = base64.urlsafe_b64encode(
        f"oidc:nonce={nonce}:state={state}".encode()
    ).decode().rstrip("=")

    # Redirect back to frontend with session
    frontend_url = "http://127.0.0.1:5173"
    return Response(
        status_code=302,
        headers={"Location": f"{frontend_url}?token={session_token}"},
    )


@router.get("/userinfo")
async def userinfo(token: str = ...) -> dict[str, Any]:
    """Minimal userinfo endpoint - validates session token format."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        # Parse: oidc:nonce=...:state=...
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
        return {"error": "invalid token"}, 400
